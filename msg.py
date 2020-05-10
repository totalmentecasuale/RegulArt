import numpy as np
from sklearn.cluster import DBSCAN

from pythonosc import dispatcher, osc_server, udp_client



class AgentCluster():
    def __init__(self, eps=50, min_samples=3):
        self.dbscan = DBSCAN(eps, min_samples=min_samples)
        self.contours = []
        self.full = False

    def reasoning(self, *msg):
        if msg[0][0] != "STOP":
            if self.full:
                self.contours = []
            self.contours.append(msg[0][0])
            self.contours.append(msg[0][1])
            self.full = False
        elif not self.full:
            samples = np.reshape(np.array(self.contours), [-1, 2])
            print("%d new samples" % samples.shape[0])
            self.full = True
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
        if self.ac.full and labels[0] is not None:
            values = labels[0]
            labels[0] = values[1:]
            print("%d clusters" % (np.unique(values).size))
            points = []
            points.append(np.unique(values).size)
            for j in range(0, np.unique(values).size):
                label = np.unique(values)[j]
                sumX = 0
                sumY = 0
                count = 0
                i = 0
                while i < len(self.ac.contours):
                    if int(i/2) < len(values):
                        k = int(i / 2)
                        if values[k] == label:
                            sumX+= self.ac.contours[i]
                            sumY+= self.ac.contours[i+1]
                            count+=1
                    i+=2
                points.append(sumX/count)
                points.append(sumY/count)

            self.client.send_message(self.name_out, points)
        else:
            self.client.send_message(self.name_out, -1)


    def action(self):
        print("... serving")
        self.server.serve_forever()


if __name__ == "__main__":  # this is run if this is the main script
    agent = AgentOSC(50)
    agent.action()
