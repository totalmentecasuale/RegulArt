import processing.video.*;
import gab.opencv.*;
import java.util.*;
import oscP5.*;
import netP5.*;

OpenCV opencv;
boolean available = false;

List<PImage> clusteringFx;

//Agente per la clusterizzazione
Agent a;
Capture cam;
OscP5 oscP5;
OscP5 audioOscP5;
NetAddress location;

//Frame attuale
PImage img;
//Frame precedente
PImage prevFrame;

int cam_w;
int cam_h;

//Soglia per motion detection --> oltre si generano particelle
float thresholdBack = 40;

boolean reg = false;

//Particelle massime ammesse nel sistema
int MAX_PARTICLES;
int step = 2;

//Lista dei clusters
List<GravityPoint> pointGravityList;

//Lista dei punti da clusterizzare (ottenuti tramite motion detection)
List<PVector> vectors;
// Semaforo per triggerare o meno l'aggiornamento in ogni loop
boolean update = false;

//Lista delle particelle del sistema, al più bands
List<Particle> particles;
List<Integer> availableBands;
PImage backgroundImage; 

float cohesM = 0.5;
float separM = 3;
float alignM = 0.5;
float fluxM = 0.5;
float clustM = 1.5;
float maxSpeedIR = 10.0;
float maxForceIR = 1.0;
float maxSpeedR = 20.0;
float maxForceR = 1.5;

float curr_volume = 0;


void setup(){
  fullScreen();
  a = new Agent();
  pointGravityList = new ArrayList<GravityPoint>();
  vectors = new ArrayList<PVector>();
  oscP5 = new OscP5(this,57121);
  audioOscP5=new OscP5(this,58121);
  location = new NetAddress("127.0.0.1",57120);
  cam_w = 80;
  cam_h = 60;
  
  cam = new Capture(this, cam_w,cam_h,30);
  opencv = new OpenCV(this, cam_w, cam_h);
  backgroundImage = createImage(cam_w, cam_h, RGB);

  cam.start();
  colorMode(RGB);
  background(0);
  MAX_PARTICLES = 729;
  availableBands = new ArrayList<Integer>();
  for(int i = 0; i < MAX_PARTICLES; i++){
     availableBands.add(i); 
  }
  
  particles = new ArrayList<Particle>(MAX_PARTICLES);
  
}

void draw(){
  loadPixels(); 
  cam.loadPixels();   
  
  fill(0,255);
  noStroke();
  rect(0,0,width, height);

  
  //==================================================//
  //  Rimozione particelle morte  //
  //==================================================//
  //controlla se ci sono particelle morte e nel caso le rimuove
  for(int i = 0; i < particles.size();){
    Particle temp_p = particles.get(i);
    if(temp_p.isDead()){
      availableBands.add(temp_p.bandId);
      particles.remove(temp_p);
    }else{
      int x_cam = int(map(temp_p.location.x, width, 0, 0, cam_w));
      int y_cam = int(map(temp_p.location.y, 0, height, 0, cam_h));
      temp_p.c = cam.pixels[x_cam + y_cam * cam_w];
      i++;

    }    
  }
  if(particles.size() < MAX_PARTICLES){
    //==================================================//
    //  Motion detection  //
    //==================================================//
    List<PVector> velPixels = new ArrayList<PVector>();
    List<PVector> movPixels = new ArrayList<PVector>();
    List<Integer> colPixels = new ArrayList<Integer>();
    //loadPixels();
    //println(f, avgFreq, sqrt(variance_freq), abs(f - avgFreq));
    //per ogni pixel dell'immagine corrente
    for(int x=0; x < cam_w - step && available; x = min(x+step, cam_w)){
      for(int y=0; y < cam_h - step && available; y = min(y+step, cam_h)){
        
        //distanza in termine di colori
        PVector d = opencv.getAverageFlowInRegion(x,y,step,step);
        if(d.magSq() > 2){
          //Se oltre la soglia (c'è movimento in quel pixel)
          int loc = x + y * cam_w; // Step 1, what is the 1D pixel location 
          color fgColor = cam.pixels[loc]; // Step 2, what is the foreground color
          color bgColor = backgroundImage.pixels[loc]; // Step 3, what is the background color 
          float r1 = red(fgColor); // Step 4, compare the foreground and background color 
          float g1 = green(fgColor); 
          float b1 = blue(fgColor); 
          float r2 = red(bgColor); 
          float g2 = green(bgColor); 
          float b2 = blue(bgColor); 
          float diff = dist(r1, g1, b1, r2, g2, b2); 
          
          //Se non è stato superato il limite di particelle massime
          if(!update && diff > thresholdBack){
            float x_new = map(x, 0, cam_w, 0, width);
            float y_new = map(y, 0, cam_h, 0, height);
            PVector p = new PVector(x_new,y_new);
            vectors.add(p);
            movPixels.add(p);
            velPixels.add(d);
            colPixels.add(color(r1,g1,b1));
          } 
        }
      }
    }
  
    //==================================================//
    //  Assegnamento particella-banda  //
    //==================================================//
    
    Collections.shuffle(movPixels);
    
    for(int i = 0; 
        i < movPixels.size(); 
        i = min(i + 1 + (movPixels.size() / MAX_PARTICLES),
                movPixels.size())){
      PVector p = movPixels.get(i);
      if(!availableBands.isEmpty() && particles.size() < MAX_PARTICLES){
        Integer band_idx = availableBands.remove((int)random(availableBands.size()));
        particles.add(new Particle(p,band_idx, colPixels.get(i), velPixels.get(i), reg));
      } 
    }
  }
   
  //==================================================//
  //  Clustering process  //
  //==================================================//
  //Se non siamo in fase di aggiornamento, il timer è scaduto
  // e ci sono punti di movimento da clusterizzare, chiama il server 
  if(!update && vectors.size() > 3){
    update = true;
    a.action(vectors);
  }
  
  //==================================================//
  //  Aggiornamento proprietà particelle  //
  //==================================================//
  //Per ogni particella attiva del sistema
  for(int i = 0; i < particles.size(); i++){
    
    if(pointGravityList != null && pointGravityList.size() > 0){
      //trova il più vicino alla posizione della particella
      List<GravityPoint> tmp = new ArrayList<GravityPoint>(pointGravityList);
      GravityPoint minDist = tmp.get(0);

      for(GravityPoint p : tmp){
        if(p.dist(particles.get(i).location) 
            < minDist.dist(particles.get(i).location)){
          minDist = p;  
        }
      }
      
      GravityPoint gp = new GravityPoint(minDist);
      particles.get(i).setCluster(gp);
    }else{
      particles.get(i).setCluster(null);
    }
          
    particles.get(i).setRegular(reg);

    //disegna il poligono
    particles.get(i).run();
  }
}

//calcola la distanza tra due pixel in termini di colori
float distSq(float x1, float x2, float y1, float y2, float z1, float z2){ 
  float d = (x2-x1)*(x2-x1) + (y2-y1)*(y2-y1) + (z2-z1)*(z2-z1);
  return d;
}

//////// user interaction ////////

//Per aumentare o diminuire dinamicamente la soglia
void keyPressed() {

  switch(key) {

    case '+':
      maxForceR += 0.005;
      println(maxForceR);
      break;
  
    case '-':
      maxForceR -= 0.005;
      println(maxForceR);
      break;
      
    case 'q':
      cohesM += 0.01;
      println(cohesM);
      break;
    
    case 'a':
      cohesM -= 0.01;
      println(cohesM);
      break;
    
    case 's':
      separM -= 0.1;
      println(separM);
      break;
      
    case 'w':
      separM += 0.1;
      println(separM);
      break;

  }
}

//Evento triggerato automaticamente dal programma quando riceve da una porta
// un messaggio Osc
void oscEvent(OscMessage msg) {
  
    if(msg.checkAddrPattern("/labels")==true) 
  {
    updateData(msg);}
  else if(msg.checkAddrPattern("/soundRepetition")==true)
  { 
    reg= msg.get(0).intValue() == 1;
    float volume_py = msg.get(1).floatValue();
    curr_volume = constrain(curr_volume + (volume_py - curr_volume) * 0.6, 0, 1);
    if(curr_volume < 0.05){
      reg = false;  
    }
  }
}

//Carica i nuovi cluster e resetta le variabili di controllo processo 
void updateData(OscMessage msg){
  
  List<PVector> list = a.reasoning(msg);
  
  if(list != null && !list.isEmpty()){
    for(PVector p : list){
      if(p.x != width / 2){
        p.x = map(p.x, 0, width, width , 0);
      }  
    }
    List<GravityPoint> tmp = new ArrayList<GravityPoint>(pointGravityList);
    for(PVector p : list){
      boolean found = false;
      for(int i = 0; i < tmp.size();){
        if(tmp.get(i).lifetime < 0){
          tmp.remove(i);
        }else if(abs(tmp.get(i).dist(p)) < 20){
          found = true;
          tmp.get(i).x = p.x;  
          tmp.get(i).y = p.y;
          break;
        }else{
          i++;
        }
      }
            
      if(!found){
         tmp.add(new GravityPoint(p));
      }
    }
    
    for(int i = 0; i < tmp.size();i++){
        tmp.get(i).lifetime--;       
    }
    pointGravityList = tmp;
  }
  vectors = new ArrayList<PVector>();
  update = false;
}

float getAvg(List<Float> list, int power){
  float avg = 0;
  for(int i = 0; i < list.size(); i++){
      avg+= pow(list.get(i), power);     
  }
  if(list.size() > 0){
    avg = avg / list.size();  
  }
  return avg;
}


float getVariance(List<Float> list){
  return getAvg(list, 2) - pow(getAvg(list,1), 2);
}


float calcLog10(float x){
  if(x>0)
  return 10 * log(x) / log(10);
  else return 0;
}

void captureEvent(Capture cam){
  cam.read();
  opencv.loadImage(cam.copy());
  opencv.calculateOpticalFlow();
  available = true;
}

void mousePressed() { 
  // Copying the current frame of video into the backgroundImage object 
  // Note copy takes 5 arguments: // The source image // x,y,width, and height of region to be copied from the source // x,y,width, and height of copy destination 
  backgroundImage.copy(cam, 0, 0, cam.width, cam.height, 0, 0, cam.width, cam. height);  
}
