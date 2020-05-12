import numpy as np
from sklearn.cluster import DBSCAN

from pythonosc import dispatcher, osc_server, udp_client



class AgentCluster():
    def __init__(self, eps=50, min_samples=3):
        self.dbscan = DBSCAN(eps, min_samples=min_samples)
        #array per le coordinate dei punti
        self.contours = []
        #variabile di controllo per gestire fine e inizio comunicazione
        self.full = False

    def reasoning(self, *msg):
        #Se il messaggio è un punto
        if msg[0][0] != "STOP":
            if self.full:
                self.contours = []
            #Aggiungi i punti all'array
            self.contours.append(msg[0][0])
            self.contours.append(msg[0][1])
            self.full = False
        #Se la comunicazione dei punti è finita
        elif not self.full:
            samples = np.reshape(np.array(self.contours), [-1, 2])
            print("%d new samples" % samples.shape[0])
            self.full = True
            #avvia clustering
            return self.dbscan.fit_predict(samples)


class AgentOSC():
    def __init__(self, eps=50, min_samples=3,
                 ip="127.0.0.1",
                 port_in=57120,
                 port_out=57121,
                 name_in="/cluster",
                 name_out="/labels"):
        self.ac = AgentCluster(eps, min_samples)
        self.name_in = name_in
        self.name_out = name_out

        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map(self.name_in, self.reasoning)
        self.client = udp_client.SimpleUDPClient(ip, port_out)

        self.server = osc_server.ThreadingOSCUDPServer(
            (ip, port_in), self.dispatcher)



    def reasoning(self, name, *data):
        labels = []
        labels.append(self.ac.reasoning(data))
        #se sono stati ricevuti tutti i punti e sono presenti delle classi
        if self.ac.full and labels[0] is not None:
            values = labels[0]
            labels[0] = values[1:]
            print("%d clusters" % (np.unique(values).size))

            #Inizializziamo un'array contenente il numero di clusters
            points = []
            points.append(np.unique(values).size)
            #Per ogni possibile classe
            for j in range(0, np.unique(values).size):
                label = np.unique(values)[j]
                sumX = 0
                sumY = 0
                count = 0
                i = 0
                #Cerchiamo i punti relativi a quella classe
                while i < len(self.ac.contours):
                    if int(i/2) < len(values):
                        k = int(i / 2)
                        if values[k] == label:
                            sumX+= self.ac.contours[i]
                            sumY+= self.ac.contours[i+1]
                            count+=1
                    i+=2

                #Calcoliamo il centroide di quella classe e lo aggiungiamo alla lista da inviare a Processing
                points.append(sumX/count)
                points.append(sumY/count)
            #Inviamo il messaggio a Processing
            self.client.send_message(self.name_out, points)
        else:
            # Inviamo il messaggio a Processing contenente un valore di default
            self.client.send_message(self.name_out, -1)


    def action(self):
        print("... serving")
        self.server.serve_forever()


if __name__ == "__main__":  # this is run if this is the main script
    agent = AgentOSC(50)
    agent.action()
