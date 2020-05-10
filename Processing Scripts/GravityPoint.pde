class GravityPoint extends PVector{
 
  PImage effect;
  PVector target;
  float lifetime = 3;
  
  GravityPoint(float x,float y, float z){
   super(x,y,z); 
   initializeEffect();
  }
  
  GravityPoint(GravityPoint gp){
   super(gp.x, gp.y, gp.z);
   initializeEffect();
   lifetime = gp.lifetime;
  }
  
  GravityPoint(PVector p){
   super(p.x, p.y, p.z); 
   initializeEffect();
  }
  
  GravityPoint(float x,float y){
   super(x,y);
   initializeEffect();
  }
  
  void initializeEffect(){
    target = new PVector(x,y);
  }
}
