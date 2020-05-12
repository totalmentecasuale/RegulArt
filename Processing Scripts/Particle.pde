class Particle{
  
  //Vettori relativi a posizione, cluster di appartenenza, velocità e accelerazione
  PVector location;
  PVector cluster;
  PVector velocity;
  PVector acc;
  
  //i vertici del poligono
  ArrayList<PVector> vertexList;
  //le velocità dei singoli vertici
  ArrayList<PVector> velocityVertexList;
  
  //stato di regolarità
  boolean regular;
  
  //massima distanza del vertice dal punto di location
  float vertLocMaxDist = 20;

  //lifetime iniziale
  int startLifetime = int(random(10,30));
  //lifetime attuale
  int lifetime = startLifetime;
  //colore
  int c;
  //numero di vertici
  int numberOfVertex;
  //posizione di riferimento in caso di regolarità
  int spotId;
  
  Particle(PVector loc,Integer spotId, int c, PVector flux, boolean reg){
    location = loc.copy();
    location.x = map(location.x, 0, width, width, 0);
    velocity = flux.copy();
    velocity.limit(maxSpeedIR);
    acc = new PVector(0,0);
    numberOfVertex = int(random(3,6));
    //la lista dei vertici del poligono sotto forma di vettori
    vertexList = new ArrayList<PVector>(numberOfVertex);
    //la lista delle velocità dei vertici del poligono sotto forma di vettori
    velocityVertexList = new ArrayList<PVector>(numberOfVertex);
    this.c = c;
    createAllVertex();
    createAllVelocityVertex();
    this.regular = reg;
    this.spotId = spotId;
  }
  
  boolean isDead(){
    return lifetime < 0 || outOfBounds();  
  }
  
  boolean outOfBounds(){
    return location.x < 0 || location.y < 0 || location.x > width || location.y > height;  
  }
  
  
  void setCluster(PVector cluster){
    if(cluster != null){
      this.cluster = cluster.copy();
    }else{
      this.cluster = null;
    }
  }
  
  void setRegular(boolean b){
    this.regular = b;
  }
  
  void applyForce(PVector force){
    acc.add(force);
  }
  
  //dato un target da raggiungere, crea una forza per raggiungere quel punto
  PVector seek(PVector target){
    PVector desired = PVector.sub(target,location);
    desired.normalize();
    desired.mult(regular ? maxSpeedR : maxSpeedIR);
    PVector steer = PVector.sub(desired,velocity);
    return steer;
  }
  
  //crea una forza relativa alla coesione del particle system
  PVector cohesion(){
    float neighDist = 50;
    PVector sum = new PVector(0,0);
    int count = 0;
    
    for(Particle p : particles){
      float dist = PVector.dist(location,p.location);
      if(!this.equals(p) && dist > neighDist){
        sum.add(p.location);
        count++;
      }
    }
    
    if(count > 0){
      sum.div(count);
      return seek(sum);
    }else{
      return sum;  
    }   
  }
  
  // crea una forza relativa all'allineamento del particle system 
  PVector align () {
    float neighbordist = 25.0;
    PVector steer = new PVector();
    int count = 0;
    for (Particle other : particles) {
      float d = PVector.dist(location,other.location);
      if ((d > 0) && (d < neighbordist)) {
        steer.add(other.velocity);
        count++;
      }
    }
    if (count > 0) {
      steer.div((float)count);
      // Implement Reynolds: Steering = Desired - Velocity
      steer.normalize();
      steer.mult(regular ? maxSpeedR : maxSpeedIR);
      steer.sub(velocity);
    }
    return steer;
  }
  
  //crea una forza relativa alla separazione delle particelle all'interno del particle system
  PVector separate(){
    float sepLevel = 30;
    PVector steer = new PVector(0,0);
    int count = 0;
    
    for(Particle p : particles){
      float d = PVector.dist(location, p.location);
      if(!p.equals(this) && d < sepLevel){
        PVector diff = PVector.sub(location, p.location);
        diff.normalize();
        diff.div(d);
        steer.add(diff);
        count++;
      }
    }
    
    if(steer.mag() > 0){
      steer.div(count); 
      steer.normalize();
      steer.mult(regular ? maxSpeedR : maxSpeedIR);
      steer.sub(velocity);
    }
    
    return steer;
    
  }
  
  //aggiorna la posizione della particella
  void updatePosition(){
    
    //comportamento per stato di irregolarità sonora
    if(!regular){
      int x_new = int(map(location.x, width, 0, 0, cam_w - step));
      int y_new = int(map(location.y, 0, height, 0, cam_h - step ));
      
      PVector flux = opencv.getAverageFlowInRegion(x_new,y_new,step,step);
      if(flux.magSq() > 0.0002){
        flux.x = -flux.x;
        flux.mult(maxSpeedIR);
        
        PVector steerFlux = PVector.sub(flux,velocity);
        applyForce(steerFlux.mult(fluxM));
      }
      
      if(cluster != null){
        applyForce(seek(cluster).mult(clustM));
      }      
      
      applyForce(separate().mult(separM));
      applyForce(cohesion().mult(cohesM));
      applyForce(align().mult(alignM));
      
      sumForcesToLocation(cluster);
      
      //FINE LOCATION
      //INIZIO VERTICI
      
      for(int i = 0; i < numberOfVertex; i++){
        updateVelocity(null, velocityVertexList.get(i), vertexList.get(i)); 
      }  
      
    }else{
      //comportamento per stato di regolarità sonora
      int maxRow = (int)Math.ceil(Math.sqrt(MAX_PARTICLES));
      int x = spotId % maxRow;
      int y = spotId / maxRow;
      int cellStepX = width/maxRow;
      int cellStepY = height/maxRow;
      PVector target = new PVector((x * cellStepX) + cellStepX / 2, (y * cellStepY) + cellStepY / 2);
      PVector desired = seek(target);
      applyForce(desired);
      sumForcesToLocation(target);
      ArrayList<PVector> targetVertex = getTargetVertexList();
      //Aggiorna i vertici in modo che la figura risulti un poligono regolare,
      //avento centro nella posizione della particella
      for(int i = 0; i < numberOfVertex; i++){
        updateVelocity(targetVertex.get(i), velocityVertexList.get(i), vertexList.get(i));
      }  
    }
    
    acc.mult(0);
  }
  
  //Aggiorna la velocità in base al pvector target
  void updateVelocity(PVector gbest, PVector velocity_vertex, PVector vertex){
    PVector tmpAcc = null;
    float approxDist = 10;
    float dist = 100;
    if(!regular){
      tmpAcc = acc.copy();
      dist = PVector.dist(location, vertex);

      if(dist > vertLocMaxDist){
        PVector desired = PVector.sub(location, vertex);
        desired.setMag(maxSpeedIR);
        PVector steer = PVector.sub(desired, velocity_vertex);
        tmpAcc.add(steer); 
      }else{
        PVector rand = PVector.random2D();
        rand.setMag(maxSpeedIR);
        tmpAcc.add(rand); 
      } 
      velocity_vertex.add(tmpAcc);
    }else{ 
      dist = PVector.dist(gbest,vertex);
      PVector desired = PVector.sub(gbest,vertex);
      desired.normalize();
      desired.mult(maxSpeedR);
      PVector steer = PVector.sub(desired, velocity_vertex);
      velocity_vertex.add(steer);
    }
    
    if(dist < approxDist){
      velocity_vertex.mult(map(dist, 0, approxDist, 0.01, 0.5));
    }
    
    vertex.add(velocity_vertex);  
  }
  
  //processo di renderizzazione del poligono
  void render(){
    pushMatrix();
    beginShape();
    float opac = map(lifetime, 0, startLifetime, 20, 255);
    fill(c, opac);
    PVector vert = vertexList.get(0);
    vertex(vert.x, vert.y);
    for(int i = 1; i < numberOfVertex; i++){
      vert = vertexList.get(i);
      vertex(vert.x, vert.y);
    }
    endShape(CLOSE);
    popMatrix();
    
    
    //gestione della lifetime
    if(!regular){
      if(curr_volume > 0.4){
        lifetime = constrain(lifetime + 1, 0, startLifetime);
      }else{
        lifetime = lifetime - 1;
      }
    }else{
      lifetime = constrain(lifetime + 1, 0, startLifetime);
    }
  }
  
  //avvia il processo di renderizzazione
  void run(){
    
    //processo di mutazione basato su un processo randomico e sulla regolarità del suono
    if(random(1) > 0.995 && regular){
      
      //il poligono cambia numero di lati e reinizializza le sue proprietà
      numberOfVertex = (int) random(3, 8);
      createAllVertex();
      createAllVelocityVertex();
    }
    
    //aggiornamento della posizione calcolando tutte le forze coinvolte
    updatePosition();
    
    //processo per la renderizzazione grafica
    try{
      render();
    }catch(Exception e){
      println("Errore assertion ", e);  
    }
  }
  
  //Restituisce la lista di vertici da raggiungere per ottenere una figura regolare
  ArrayList<PVector> getTargetVertexList() {
    ArrayList<PVector> vectorList = new ArrayList<PVector>(numberOfVertex);
    float angle = TWO_PI / numberOfVertex;
    for (float a = 0; a < TWO_PI; a += angle) {
      float sx = location.x + cos(a) * (width + height) / MAX_PARTICLES * map(curr_volume, 0, 1, 5, 10);
      float sy = location.y + sin(a) * (width + height) / MAX_PARTICLES * map(curr_volume, 0, 1, 5, 10);
      vectorList.add(new PVector(sx, sy));
    }
    
    return vectorList;
  }
  
  
  //Crea tutti i vertici della da disegnare
  private void createAllVertex(){
    for(int i = 0; i < numberOfVertex; i++){
      float x = location.x;
      float y = location.y;
      float deltaX = random(5,10);
      float deltaY = random(5,10);
      
      if(random(1)> 0.5){ // sommaX
        if(x + deltaX > width){
            deltaX = -deltaX;
        }
      }else{ //sottraiX
          if(x - deltaX > 0){
            deltaX = -deltaX;
          }
      }
      
      if(random(1)> 0.5){ // sommaY
        if(y + deltaY > height){
            deltaY = -deltaY;
        }
      }else{ //sottraiY
          if(y - deltaY > 0){
            deltaY = -deltaY;
          }
      }
      
      vertexList.add(new PVector(x + deltaX, y + deltaY));   
    }
  
  }
  
  void createAllVelocityVertex(){
    for(int i = 0; i < numberOfVertex; i++){
      velocityVertexList.add(new PVector(0,0));  
    }
  }
  
  //metodo finale che modifica la posizione del poligono e regola le forze
  void sumForcesToLocation(PVector target){
    float apprDist = 10;
    acc.limit(regular ? maxForceR : maxForceIR);
    velocity.add(acc);
    if(target != null){
      float dist = PVector.dist(target,location);
      if(dist < apprDist){
        float coeff = map(dist, 0, apprDist, 0.005, 0.1);
        velocity.mult(coeff);
      }
    }
    location.add(velocity);  
  }
  
}
