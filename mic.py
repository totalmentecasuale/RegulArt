import pyaudio
import numpy as np
from scipy.fftpack import fft, ifft
from pythonosc import udp_client
import math


class AgentRepetition():
    def __init__(self,
                 ip="127.0.0.1",
                 port_out=58121,
                 name_out="/soundRepetition",
                 CHANNELS=1, RATE=8000,
                 FORMAT=pyaudio.paInt16,

                 # ---USER PARAMETERS
                 msec=50,  # millisecondi da leggere
                 sec_investigate=0.5,
                 saved_exec=10):

        last_msec = msec  # millisecondi da comparare con sec TRASFORMA IN MILLISEC
        CHUNK = pow(2, math.ceil(math.log(RATE * (msec / 1000), 2)))
        n_frames_s = int(math.ceil(RATE / CHUNK))  # num esatto di frames in ogni secondo
        n_f_ms = int(
            math.ceil((msec / pow(10, 3)) * n_frames_s))  # num esatto di frames del segnale base in ogni MILLIsecondi
        n_f_last_ms = int(math.ceil((last_msec / pow(10,
                                                     3)) * n_frames_s))  # num esatto di frames del segnale da ricare in quello base in ogni MILLIsecondi

        # pyaudio class instance
        p = pyaudio.PyAudio()


        # stream object to get data from microphone
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=CHUNK
        )

        self.name_out = name_out

        self.client = udp_client.SimpleUDPClient(ip, port_out)

        print('stream started')

        # for measuring frame rate
        i = 0

        # for measuring the presence of sound/silence
        maxVol = 1
        minVol = 0
        volume = 0
        presenceOfSound = False
        last_msg = False
        # to look for repetitions
        repetition = False
        rep_saved = np.array(repetition)
        tot_elms_in_whole_audio = int(sec_investigate / (msec * pow(10, -3)))

        while True:
            if i == 0:  # Reading first number of msecond and filling the buffer
                for jj in range(0, tot_elms_in_whole_audio):
                    for j in range(0, n_f_ms):  # salvo il numero di millisecondi richiesti dall'utente nel segnale bas
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        data = np.frombuffer(data, dtype=np.int16)

                        volume = int((np.linalg.norm(data) * 10) / (math.pow(10, 3)))
                        if volume > maxVol:
                            maxVol = volume
                            minVol = maxVol * 0.005
                        if volume < minVol:
                            presenceOfSound = False
                        else:
                            presenceOfSound = True

                        data_to_append = np.reshape(data, (1, CHUNK))

                        if (j == 0):
                            frames = np.array(data, ndmin=2)

                        else:
                            frames = np.append(frames, data_to_append, axis=1)

                    if jj == 0:
                        whole_audio = frames
                    else:
                        whole_audio = np.append(whole_audio, frames, axis=0)
                i += 1

            else:
                k = 0

                for ii in range(0, n_f_last_ms):  # salvo i secondi con cui confrontare il segnale base
                    data = stream.read(CHUNK, exception_on_overflow=False)
                    data = np.frombuffer(data, dtype=np.int16)

                    volume = int((np.linalg.norm(data) * 10) / (math.pow(10, 3)))
                    if volume > maxVol:
                        maxVol = volume
                        minVol = maxVol * 0.005

                    if volume < minVol:
                        presenceOfSound = False
                    else:
                        presenceOfSound = True

                    if k == 0:
                        last_frames = np.array(data, ndmin=2)
                    else:
                        data_to_append_lf = np.reshape(data, (1, CHUNK))
                        last_frames = np.append(last_frames, data_to_append_lf, axis=1)
                k += 1

                # Perform autocorrelation
                corr_vect = np.array(0, ndmin=2)

                for hh in range(0, np.size(whole_audio, 0)):

                    corr = correlation(whole_audio[hh, :], last_frames[0, :])
                    if hh == 0:
                        corr_vect = np.array(corr, ndmin=2)

                else:
                    corr = np.reshape(corr, (1, len(corr)))
                    corr_vect = np.append(corr_vect, corr, axis=1)

                media = corr_vect.mean()

                if media > 0.2 and volume > minVol:
                    repetition = True
                else:
                    repetition = False
                #print(volume, maxVol, minVol)
                # handle fake negatives and fake positives:
                fn = 0
                fp = 0
                rep_to_send = repetition

                if rep_saved.size == saved_exec:
                    for a in range(rep_saved.size):
                        if not rep_saved[a]:
                            fn += 1
                        elif a >= rep_saved.size - int(saved_exec / 5):
                            fp += 1

                    if fp == int(saved_exec / 5):
                        rep_to_send = True
                    elif fn == saved_exec:
                        rep_to_send = False
                    else:
                        rep_to_send = last_msg

                    print(rep_to_send, presenceOfSound, rep_saved)

                rep_saved = np.append(rep_saved, repetition)

                if rep_saved.size > saved_exec:
                    rep_saved = rep_saved[1:]

                whole_audio = np.append(whole_audio, last_frames, axis=0)
                whole_audio = whole_audio[1:, :]
                last_msg = rep_to_send

                if rep_to_send:
                    msg_rep = 1
                else:
                    msg_rep = 0


                self.client.send_message(self.name_out, [msg_rep, float(volume / maxVol)])


def correlation(x, y):
    c = ifft(fft(x) * np.conj(fft(y))) / (np.linalg.norm(x) * np.linalg.norm(y))
    for h in range(0, len(c)):
        r = np.real(c[h])
        r = pow(r, 2)
        i = np.imag(c[h])
        i = pow(i, 2)
        c[h] = pow(r + i, 1 / 2)
    return c

if __name__ == "__main__":  # this is run if this is the main script
    agent = AgentRepetition()


