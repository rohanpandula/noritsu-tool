"""C-41 negative inversion in density space (Noritsu-style).

The scanner measures transmittance. We convert to density D=-log10(T),
remove the per-channel orange mask (Dmin), normalize by the density range,
and produce a positive. Working in density space is what Noritsu/Frontier
minilabs do and it resolves the complementary-dye color inversion naturally.
"""
import numpy as np

EPS = 1e-6


def to_density(linear, black=0.0):
    """Convert linear transmittance [0,1] to density. black = scanner black level."""
    v = np.clip(linear - black, EPS, None)
    # normalize so max possible transmittance maps to density 0
    return -np.log10(v)


def estimate_dmin(density, percentile=0.5, mask=None):
    """Estimate per-channel Dmin (film base + fog = orange mask).

    Dmin is the *minimum* density, found in the clearest film areas
    (border / brightest highlights). We take a low percentile for robustness.
    """
    d = density if mask is None else density[mask]
    return np.percentile(d.reshape(-1, 3), percentile, axis=0)


def estimate_dmax(density, percentile=99.8, mask=None):
    """Estimate per-channel Dmax (densest meaningful image area)."""
    d = density if mask is None else density[mask]
    return np.percentile(d.reshape(-1, 3), percentile, axis=0)


def border_mask(shape, frac=0.03):
    """Boolean mask of the outer ring (film rebate/border), if present."""
    h, w = shape[0], shape[1]
    m = np.zeros((h, w), dtype=bool)
    bh = max(1, int(h * frac))
    bw = max(1, int(w * frac))
    m[:bh, :] = True
    m[-bh:, :] = True
    m[:, :bw] = True
    m[:, -bw:] = True
    return m


def film_valid_mask(linear, black_th=0.005, clear_th=0.9):
    """Boolean mask of on-film pixels, excluding clear (non-film) margins and
    black scan borders, so density statistics reflect the film only."""
    mx = linear.max(axis=2)
    return (mx < clear_th) & (mx > black_th)


def crop_to_film(linear, pad=0, min_frac=0.3, row_thresh=0.5):
    """Crop to the film frame, dropping clear margins and black scan borders.

    Keeps rows/cols where a majority of pixels are on-film, so thin clear
    strips and black bars (which contain some non-zero pixels) are excluded.
    Returns (cropped, bbox)."""
    m = film_valid_mask(linear, black_th=0.03)
    if m.mean() < min_frac:
        return linear, (0, linear.shape[0], 0, linear.shape[1])
    row_frac = m.mean(axis=1)
    col_frac = m.mean(axis=0)
    rows = np.where(row_frac > row_thresh)[0]
    cols = np.where(col_frac > row_thresh)[0]
    if rows.size == 0 or cols.size == 0:
        return linear, (0, linear.shape[0], 0, linear.shape[1])
    r0, r1 = rows[0], rows[-1] + 1
    c0, c1 = cols[0], cols[-1] + 1
    r0 = max(0, r0 - pad); c0 = max(0, c0 - pad)
    r1 = min(linear.shape[0], r1 + pad); c1 = min(linear.shape[1], c1 + pad)
    return linear[r0:r1, c0:c1], (r0, r1, c0, c1)


def estimate_dmin_border(density, frac=0.03):
    """Estimate Dmin from the film rebate (outer ring).

    The unexposed rebate is pure orange mask: high density with B > G > R.
    If the border looks like mask, return its per-channel median density;
    otherwise return None (caller falls back to percentile).
    """
    m = border_mask(density.shape, frac)
    d = density[m]  # (N,3)
    med = np.median(d, axis=0)
    std = d.std(axis=0)
    # A true rebate is UNIFORM (low std) and reads as orange mask:
    # blue channel densest (orange absorbs blue), all fairly high.
    if med[2] > med[1] >= med[0] - 1e-3 and med.mean() > 0.1 and std.mean() < 0.15:
        return med.astype(np.float32)
    return None


def invert_negative(
    linear,
    black=0.0,
    dmin=None,
    dmax=None,
    dmin_percentile=0.5,
    dmax_percentile=99.95,
    clip_shadow=0.0,
    clip_highlight=0.0,
    mask=None,
    use_border=True,
):
    """Invert a linear C-41 negative scan to a linear positive in density-normalized space.

    Returns:
        positive: float32 (H,W,3) in [0,1], where 1 = densest negative (brightest scene).
        meta: dict with dmin/dmax used.
    """
    density = to_density(linear, black=black)
    if mask is None:
        mask_dmin = film_valid_mask(linear, black_th=0.0)   # black bars don't affect min
        # exclude only true scan black (linear ~0), NOT dense film: the
        # densest negative pixels are the scene's brightest highlights
        mask_dmax = film_valid_mask(linear, black_th=0.0005)
    else:
        mask_dmin = mask_dmax = mask

    if dmin is None:
        dmin = None
        if use_border:
            dmin = estimate_dmin_border(density)
        if dmin is None:
            dmin = estimate_dmin(density, dmin_percentile, mask_dmin)
    else:
        dmin = np.asarray(dmin, dtype=np.float32)
    if dmax is None:
        dmax = estimate_dmax(density, dmax_percentile, mask_dmax)
    else:
        dmax = np.asarray(dmax, dtype=np.float32)

    # guard against degenerate range
    rng = dmax - dmin
    rng = np.where(rng < 0.05, 0.05, rng)

    # scene density: remove mask, normalize to [0,1]; high = bright scene
    norm = (density - dmin[None, None, :]) / rng[None, None, :]
    # clip borders (film rebate can exceed the image density range)
    lo = clip_shadow
    hi = 1.0 + clip_highlight
    norm = (norm - lo) / (hi - lo)
    positive = np.clip(norm, 0.0, 1.0)

    meta = {"dmin": dmin, "dmax": dmax, "range": rng}
    return positive.astype(np.float32), meta
