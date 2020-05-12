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
                 CHANNELS=1,  # canale mono
                 RATE=8000,  # rate= samples per second -->
                 # 8k anzichè il solito 44100 per velocizzare (aiuta anche a trovare ripetizioni)
                 FORMAT=pyaudio.paInt16,  # audio format:here it stores those sample data as a 16-bit integer value.

                 # ---USER PARAMETERS
                 msec=50,  # millisecondi da leggere
                 sec_investigate=0.5,  # grandezza del buffer che viene riempito da segmenti di msec
                 saved_exec=10):  # lunghezza buffer con i risulati delle correlazioni --> per falsi positivi/negativi

        # millisecondi da comparare con sec TRASFORMA IN MILLISEC
        last_msec = msec
        # i chunk calcolati così per avere sempre una potenza di 2
        CHUNK = pow(2, math.ceil(math.log(RATE * (msec / 1000), 2)))
        # num esatto di frames in ogni secondo
        n_frames_s = int(math.ceil(RATE / CHUNK))
        # num esatto di frames del segnale base in ogni MILLIsecondi
        n_f_ms = int(math.ceil((msec / pow(10, 3)) * n_frames_s))
        # num esatto di frames del segnale da ricare in quello base in ogni MILLIsecondi
        n_f_last_ms = int(math.ceil((last_msec / pow(10, 3)) * n_frames_s))

        p = pyaudio.PyAudio()

        # Apertura stream del microfono
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            output=True,
            frames_per_buffer=CHUNK
        )

        self.name_out = name_out

        # Definizione della porta di output
        self.client = udp_client.SimpleUDPClient(ip, port_out)

        print('stream started')

        i = 0

        # variabili di appoggio
        maxVol = 1
        minVol = 0
        volume = 0
        presenceOfSound = False

        # Variabile di appoggio relativa all'ultimo messaggio inviato
        last_msg = False

        repetition = False

        rep_saved = np.array(repetition)

        # il numero totale di elementi su cui fare la corr è dato da quanti segmenti da msec ci sono in sec_investigate
        # pow(10,-3) è fatto per passare millisecondi a secondi
        tot_elms_in_whole_audio = int(sec_investigate / (msec * pow(10, -3)))

        while True:
            # Se il buffer non è pieno, leggi il primo blocco da confrontare con il successivo
            if i == 0:

                # il buff è composto da un numero di elementi pari a tot_elms_in_whole_audi
                # in ognuno di questi elementi salvo un array di dati presi dallo stream audio e lunghi msec

                for jj in range(0, tot_elms_in_whole_audio):
                    # salvo il numero di millisecondi richiesti dall'utente nel segnale bas
                    for j in range(0, n_f_ms):
                        data = stream.read(CHUNK, exception_on_overflow=False)
                        data = np.frombuffer(data, dtype=np.int16)

                        # calcolo ampiezza
                        # ovviamente linalg.norm(data) trova la norma dell'array
                        volume = int((np.linalg.norm(data) * 10) / (math.pow(10, 3)))

                        # Aggiorniamo il valore del volume massimo in cui quello attuale supera il valore massimo corrente
                        if volume > maxVol:
                            maxVol = volume
                            # min vol si aggiorna in modo dinamico (0.005 trovato empiricamente)
                            minVol = maxVol * 0.005

                        # Verifichiamo che le condizioni di volume garantiscano la presenza di suono
                        if volume < minVol:
                            presenceOfSound = False
                        else:
                            presenceOfSound = True

                        # cambio dinmesione dati per poterli aggiungere a frames (e quindi anche a whole audio)
                        data_to_append = np.reshape(data, (1, CHUNK))

                        # frames= frammenti di msec che sto leggendo ora
                        if (j == 0):
                            frames = np.array(data, ndmin=2)

                        else:
                            frames = np.append(frames, data_to_append, axis=1)

                    # Salviamo i dati correnti nell'array contenente le esecuzioni da confrontare
                    if jj == 0:
                        whole_audio = frames
                    else:
                        whole_audio = np.append(whole_audio, frames, axis=0)
                i += 1


            # Se sono presenti abbastanza esecuzioni, valutiamo se c'è corrispondenza negli ultimi secondi specificati
            # dal parametro sec_investigate per vedere se c'è correlazione in uno degli slot
            else:
                k = 0

                # Acquisiamo i dati correnti dal microfono e ripetiamo il processo di inizializzazione sopra
                for ii in range(0, n_f_last_ms):
                    # ( n_f_last_ms corrisponde ad un chunck da msec)
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

                    # array per il salvataggio del risultato dell'autocorrelazione
                    corr_vect = np.array(0, ndmin=2)

                    # Per ogni esecuzione presente nell'array contenente le esecuzioni passate
                    for hh in range(0, np.size(whole_audio, 0)):

                        # faccio la correlazione tra una riga di whole audio (un segmento da msec) e l'array di last_frame
                        # e poi passo alla riga successiva di whole audio
                        corr = correlation(whole_audio[hh, :], last_frames[0, :])

                        # Salviamo il risultato
                        if hh == 0:
                            corr_vect = np.array(corr, ndmin=2)

                        else:
                            corr = np.reshape(corr, (1, len(corr)))
                            corr_vect = np.append(corr_vect, corr, axis=1)

                    # per vedere se c'è ripetizione calcolo la media dei vettori risulanti
                media = corr_vect.mean()

                # Definiamo se c'è o meno ripetizione valutando la presenza di suono e confrontando la media con una soglia
                # 0.2 è stato trovato empiricamente
                if media > 0.2 and volume > minVol:
                    repetition = True
                else:
                    repetition = False

                # Processo per gestire falsi positivi e falsi negativi
                fn = 0
                fp = 0
                # di default nel messaggio inviato c'è un valore pari a quello di repetition
                rep_to_send = repetition

                # quando ho salvato un numero di risulati pari a quelli richiesti per verificare
                if rep_saved.size == saved_exec:
                    # Controlla ogni esecuzione
                    for a in range(rep_saved.size):
                        # Aggiorna le variabili relative a risultati negativi e positivi
                        if not rep_saved[a]:
                            fn += 1

                        # Nel caso dei risultati positivi, guarda solo la porzione finale pari al 20% della lunghezza dell'array, in modo da essere più reattivo
                        elif a >= rep_saved.size - int(saved_exec / 5):
                            fp += 1

                    # se la porzione relativa al 20% dell'array di risultati risulta avere tutti true, mando true
                    if fp == int(saved_exec / 5):
                        rep_to_send = True
                        # se tutto l'array è pieno di false, mando false anche se è arrivato true
                    elif fn == saved_exec:
                        rep_to_send = False
                    # in tutti gli altri casi non cambiare il messaggio inviato precedentemente
                    else:
                        rep_to_send = last_msg

                    print(rep_to_send, presenceOfSound, rep_saved)

                # salvo il nuovo valore della ripetizione (NON modificato)
                rep_saved = np.append(rep_saved, repetition)

                # Esegui uno slice dell'array nel caso in cui la grandezza massima sia stata raggiunta
                if rep_saved.size > saved_exec:
                    rep_saved = rep_saved[1:]

                whole_audio = np.append(whole_audio, last_frames, axis=0)
                whole_audio = whole_audio[1:, :]
                last_msg = rep_to_send

                if rep_to_send:
                    msg_rep = 1
                else:
                    msg_rep = 0

                # Invia il messaggio a Processing comunicando qual è il risultato della correlazione e la porzione di volume attuale sul massimo volume
                self.client.send_message(self.name_out, [msg_rep, float(volume / maxVol)])


def correlation(x, y):
    c = ifft(fft(x) * np.conj(fft(y))) / (np.linalg.norm(x) * np.linalg.norm(y))
    # per ogni elemento dell'array c, si trova la norma per poter poi calcolare la media
    for h in range(0, len(c)):
        r = np.real(c[h])
        r = pow(r, 2)
        i = np.imag(c[h])
        i = pow(i, 2)
        c[h] = pow(r + i, 1 / 2)

    return c


if __name__ == "__main__":
    agent = AgentRepetition()


