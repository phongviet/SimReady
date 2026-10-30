"""Differentiable study objectives; no CUDA dependency required for analytic tests."""

import torch.nn.functional as F


def uniform_ssim(x, y):
    """Valid 7x7 uniform-window SSIM, population moments, RGB in [0,1]."""
    x, y = (a.permute(2, 0, 1)[None] for a in (x, y))

    def avg(a):
        return F.avg_pool2d(a, 7, stride=1)

    ux, uy = avg(x), avg(y)
    vx, vy, cov = avg(x * x) - ux * ux, avg(y * y) - uy * uy, avg(x * y) - ux * uy
    return (
        ((2 * ux * uy + 0.01**2) * (2 * cov + 0.03**2))
        / ((ux * ux + uy * uy + 0.01**2) * (vx + vy + 0.03**2))
    ).mean()


def objectives(rgb, target, depth, reference, alpha, config):
    l1 = (rgb - target).abs().mean()
    mode = config.get("photometric_loss", "l1")
    ssim = uniform_ssim(rgb.clamp(0, 1), target) if mode == "l1_ssim" else None
    photo = {
        "l1": lambda: l1,
        "mse": lambda: ((rgb - target) ** 2).mean(),
        "l1_ssim": lambda: (1 - config["ssim_weight"]) * l1 + config["ssim_weight"] * (1 - ssim),
    }[mode]()
    valid = reference > 0
    if config.get("depth_mask", "alpha") == "alpha":
        valid = valid & (alpha > 0.01)
    error = (depth[valid] - reference[valid]).abs()
    mode = config.get("depth_supervision", "l1")
    if mode == "relative_l1":
        error = error / reference[valid].clamp_min(0.05)
    depth_loss = error.mean() if error.numel() and mode != "none" else l1 * 0
    return photo + config["depth_loss_weight"] * depth_loss, {
        "rgb_l1": l1,
        "photometric": photo,
        "depth_objective": depth_loss,
        "depth_valid_fraction": valid.float().mean(),
        **({"ssim": ssim} if ssim is not None else {}),
    }
