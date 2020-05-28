import numpy as np
import pyaudio
from numpy.lib import stride_tricks
from scipy.signal import lfilter, lfilter_zi, butter, stft
from pythonosc import udp_client
from scipy.spatial import distance


# Constants
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
CHUNK = 2048
RECORD_SECONDS = 0.1
# Number of windows to analyse
win_no = 10
ip = "127.0.0.1"
port_out = 58121
name_out = "/soundRepetition"
max_rms = None
#Thresholds
corr_thresh = 0.75
regularity_thresh = 0.005


#Regularity definition
def calculate_regularity(features_list, prev_feature_list):
    msg_to_processing = 0

    res_corr = features_list[5]
    if res_corr > corr_thresh:
        msg_to_processing = 1
    else:
        norm_now_features = features_list / np.linalg.norm(features_list)
        norm_prev_features = [fv / np.linalg.norm(fv) for fv in prev_feature_list]
        dist_vect_features = np.min([distance.euclidean(norm_now_features, dist_prev_fv) for dist_prev_fv in norm_prev_features])

        if dist_vect_features < regularity_thresh and res_corr > corr_thresh / 2:
            msg_to_processing = 1

    return msg_to_processing

#Filter definition
def butter_bandpass(lowcut=40, highcut=2000, fs=RATE, order=2):
    nyq = 0.5 * fs
    low = lowcut / nyq
    high = highcut / nyq
    b, a = butter(order, [low, high], btype='band')
    return b, a


#Applying filter to the signal
def butter_bandpass_filter(data, b, a):
    zi = lfilter_zi(b, a)
    y = lfilter(b, a, data, zi=zi*data[0])
    return y


# Performing zero crossing rate
def zero_crossing_rate(wavedata):
    return np.nan_to_num(np.asarray(0.5 * np.mean(np.abs(np.diff(np.sign(wavedata[:]))))))

# Performing RMS
def root_mean_square(wavedata):
    rms = np.asarray(np.sqrt((np.mean(wavedata[:] ** 2))))

    return np.nan_to_num(rms)

# Performing spectral centroid
def spectral_centroid(magnitude_spectrum):

    timebins, freqbins = np.shape(magnitude_spectrum)
    sc = []

    for t in range(timebins-1):
        power_spectrum = np.abs(magnitude_spectrum[t])**2
        sc_t = np.sum(power_spectrum * np.arange(1,freqbins+1)) / np.sum(power_spectrum)
        sc.append(sc_t)

    sc = np.nan_to_num(sc)

    return sc[0]

# Performing spectral rolloff
def spectral_rolloff(magnitude_spectrum, sample_rate=RATE, k=0.85):

    # convert to frequency domain
    power_spectrum = np.abs(magnitude_spectrum)**2
    timebins, freqbins = np.shape(magnitude_spectrum)

    sr = []
    spectralSum = np.sum(power_spectrum, axis=1)

    for t in range(timebins-1):
        # find frequency-bin indeces where the cummulative sum of all bins is higher
        # than k-percent of the sum of all bins. Lowest index = Rolloff
        sr_t = np.where(np.cumsum(power_spectrum[t,:]) >= k * spectralSum[t])[0][0]
        sr.append(sr_t)

    sr = np.asarray(sr).astype(float)
    # convert frequency-bin index to frequency in Hz
    sr = (sr / freqbins) * (sample_rate / 2.0)

    return np.nan_to_num(sr[0])

# Performing spectral flux
def spectral_flux(magnitude_spectrum):

    # convert to frequency domain
    timebins, freqbins = np.shape(magnitude_spectrum)

    sf = np.sqrt(np.sum(np.diff(np.abs(magnitude_spectrum))**2, axis=1)) / freqbins

    return np.nan_to_num(sf[1:][0])

# Performing normalised cross-correlation
def norm_corr(a, filt_data):
    a_norm = a / np.linalg.norm(a)
    b_norm = filt_data / np.linalg.norm(filt_data)
    c = np.corrcoef(a_norm, b_norm)
    return c[0][1]

def compute(data, bp_b, bp_a):
    signal_sftf = stft(data, CHUNK)[2];
    zcr = zero_crossing_rate(data)
    rms = root_mean_square(data)
    sc = spectral_centroid(signal_sftf)
    sr = spectral_rolloff(signal_sftf)
    sf = spectral_flux(signal_sftf)
    res_corr = 0
    filtered_temp, zo = butter_bandpass_filter(data, bp_b, bp_a)
    if prev_frames:
        corr_temp = [norm_corr(prev, filtered_temp) for prev in prev_frames]
        if len(corr_temp) > 0: res_corr = np.max(corr_temp)
    return [zcr, rms, sc, sr, sf, res_corr], filtered_temp


audio = pyaudio.PyAudio()

# start Recording
stream = audio.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)
print("recording...")


prev_frames = []
# Bandpass filter coefficients
bp_b, bp_a = butter_bandpass()
prev_feature_vect = []

client = udp_client.SimpleUDPClient(ip, port_out)

while True:
    for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        frames = stream.read(CHUNK, exception_on_overflow=False)
        data = np.frombuffer(frames, dtype=np.float32)

    features, filtered_data = compute(data, bp_b, bp_a)
    prev_frames.append(filtered_data)
    if len(prev_frames) > win_no: prev_frames = prev_frames[1:]

    if prev_feature_vect:
        msg = calculate_regularity(features, prev_feature_vect)
        rms = features[1]

        if not max_rms or rms > max_rms:
            max_rms = rms

        client.send_message(name_out, [msg, float(rms/max_rms)])

    prev_feature_vect.append(features)
    if len(prev_feature_vect) > win_no: prev_feature_vect = prev_feature_vect[1:]
