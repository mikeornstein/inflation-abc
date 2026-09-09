//! SIMD SoA pressure-ladder interpolator (ORN-49).
//! Equilibria stay in the Chiron JS solver; scrub only lerps precomputed rungs.
#![no_std]

use core::arch::wasm32::*;

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}

const ALIGN: u32 = 16;
extern "C" {
    static __heap_base: u8;
}
static mut HEAP: u32 = 0;

unsafe fn heap_base() -> u32 {
    &__heap_base as *const u8 as u32
}

unsafe fn grow_to(bytes: u32) {
    let need_pages = ((bytes + 65535) / 65536) as usize;
    let have = memory_size(0);
    if need_pages > have {
        let _ = memory_grow(0, need_pages - have);
    }
}

/// 16-byte-aligned bump alloc. Call `reset_heap` before a new ladder.
#[no_mangle]
pub unsafe extern "C" fn alloc(nbytes: u32) -> u32 {
    if HEAP == 0 {
        HEAP = heap_base();
    }
    let p = (HEAP + (ALIGN - 1)) & !(ALIGN - 1);
    let end = p.saturating_add(nbytes).saturating_add(64);
    grow_to(end);
    HEAP = p + nbytes;
    p
}

#[no_mangle]
pub unsafe extern "C" fn reset_heap() {
    HEAP = heap_base();
}

#[inline]
unsafe fn load_u(p: *const f32) -> v128 {
    v128_load(p as *const v128)
}

/// Pack interleaved xyz[n*3] → SoA x[n], y[n], z[n]. Pads n up to multiple of 4 with 0.
#[no_mangle]
pub unsafe extern "C" fn pack_soa(n: u32, xyz: *const f32, x: *mut f32, y: *mut f32, z: *mut f32) {
    let n = n as usize;
    let np = (n + 3) & !3;
    for i in 0..n {
        *x.add(i) = *xyz.add(i * 3);
        *y.add(i) = *xyz.add(i * 3 + 1);
        *z.add(i) = *xyz.add(i * 3 + 2);
    }
    for i in n..np {
        *x.add(i) = 0.0;
        *y.add(i) = 0.0;
        *z.add(i) = 0.0;
    }
}

#[inline]
unsafe fn lerp_vec(w0: v128, w1: v128, a: *const f32, b: *const f32) -> v128 {
    f32x4_add(f32x4_mul(w0, load_u(a)), f32x4_mul(w1, load_u(b)))
}

/// SIMD SoA lerp → interleaved xyz_out[n*3].
/// w0+w1 should be 1. Exact rung when one weight is 0.
#[no_mangle]
pub unsafe extern "C" fn lerp_soa(
    n: u32,
    w0: f32,
    w1: f32,
    x0: *const f32,
    y0: *const f32,
    z0: *const f32,
    x1: *const f32,
    y1: *const f32,
    z1: *const f32,
    xyz_out: *mut f32,
) {
    let n = n as usize;
    let vw0 = f32x4_splat(w0);
    let vw1 = f32x4_splat(w1);
    let mut i = 0;
    while i + 4 <= n {
        let x = lerp_vec(vw0, vw1, x0.add(i), x1.add(i));
        let y = lerp_vec(vw0, vw1, y0.add(i), y1.add(i));
        let z = lerp_vec(vw0, vw1, z0.add(i), z1.add(i));
        *xyz_out.add(i * 3) = f32x4_extract_lane::<0>(x);
        *xyz_out.add(i * 3 + 1) = f32x4_extract_lane::<0>(y);
        *xyz_out.add(i * 3 + 2) = f32x4_extract_lane::<0>(z);
        *xyz_out.add((i + 1) * 3) = f32x4_extract_lane::<1>(x);
        *xyz_out.add((i + 1) * 3 + 1) = f32x4_extract_lane::<1>(y);
        *xyz_out.add((i + 1) * 3 + 2) = f32x4_extract_lane::<1>(z);
        *xyz_out.add((i + 2) * 3) = f32x4_extract_lane::<2>(x);
        *xyz_out.add((i + 2) * 3 + 1) = f32x4_extract_lane::<2>(y);
        *xyz_out.add((i + 2) * 3 + 2) = f32x4_extract_lane::<2>(z);
        *xyz_out.add((i + 3) * 3) = f32x4_extract_lane::<3>(x);
        *xyz_out.add((i + 3) * 3 + 1) = f32x4_extract_lane::<3>(y);
        *xyz_out.add((i + 3) * 3 + 2) = f32x4_extract_lane::<3>(z);
        i += 4;
    }
    while i < n {
        *xyz_out.add(i * 3) = w0 * *x0.add(i) + w1 * *x1.add(i);
        *xyz_out.add(i * 3 + 1) = w0 * *y0.add(i) + w1 * *y1.add(i);
        *xyz_out.add(i * 3 + 2) = w0 * *z0.add(i) + w1 * *z1.add(i);
        i += 1;
    }
}

/// Scalar lerp of a small f32 array (λ).
#[no_mangle]
pub unsafe extern "C" fn lerp_scalar(n: u32, w0: f32, w1: f32, a: *const f32, b: *const f32, o: *mut f32) {
    for i in 0..n as usize {
        *o.add(i) = w0 * *a.add(i) + w1 * *b.add(i);
    }
}

#[no_mangle]
pub extern "C" fn simd_level() -> u32 {
    128
}
