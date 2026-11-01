"""Small offline FIR downsampler; avoids a full SciPy dependency."""
def downsample_48k(audio):
    import numpy as np
    samples=np.asarray(audio,dtype=np.float32)
    if samples.ndim!=1:raise ValueError('Expected mono audio')
    if not len(samples):return samples
    x=np.arange(63,dtype=np.float64)-31
    kernel=np.sinc(x/3)*np.hamming(63)
    kernel/=kernel.sum()
    filtered=np.convolve(np.pad(samples,(31,31)),kernel,mode='valid')
    return filtered[::3].astype(np.float32)
