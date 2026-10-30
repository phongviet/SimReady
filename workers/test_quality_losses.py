"""Run with .venv-gpu/bin/python workers/test_quality_losses.py (Torch CPU math)."""

import torch
from quality_losses import objectives, uniform_ssim

torch.set_num_threads(2)
x = torch.full((9, 9, 3), 0.4, requires_grad=True)
y = torch.full_like(x, 0.5)
z = torch.full((9, 9), 2.0, requires_grad=True)
ref = torch.full_like(z, 4.0)
a = torch.ones_like(z)
assert torch.allclose(uniform_ssim(x, x), torch.tensor(1.0))
for mode, expected in [("l1", 0.1), ("mse", 0.01)]:
    loss, c = objectives(x, y, z, ref, a, dict(photometric_loss=mode, depth_loss_weight=0.0))
    assert abs(loss.item() - expected) < 1e-6
for mode, expected in [("l1", 2.0), ("relative_l1", 0.5), ("none", 0.0)]:
    loss, c = objectives(x, y, z, ref, a, dict(depth_supervision=mode, depth_loss_weight=0.05))
    assert abs(c["depth_objective"].item() - expected) < 1e-6
    loss.backward(retain_graph=True)
    assert torch.isfinite(x.grad).all()
for mask in ("alpha", "gt_valid"):
    loss, c = objectives(
        x,
        y,
        z,
        ref,
        a * 0,
        dict(photometric_loss="l1_ssim", ssim_weight=0.2, depth_mask=mask, depth_loss_weight=0.05),
    )
    loss.backward(retain_graph=True)
    assert torch.isfinite(loss) and torch.isfinite(z.grad).all()
    assert c["depth_valid_fraction"].item() == (0 if mask == "alpha" else 1)
loss, c = objectives(x, y, z, ref * 0, a, dict(depth_loss_weight=0.05))
assert c["depth_objective"] == 0
print("PASS: analytic L1/MSE/SSIM/depth objectives, empty masks, finite gradients (Torch CPU)")
