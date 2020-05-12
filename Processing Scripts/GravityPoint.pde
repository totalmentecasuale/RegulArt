class GravityPoint extends PVector{
 
  //lifetime del punto di cluster
  float lifetime = 3;
  
  GravityPoint(float x,float y, float z){
   super(x,y,z); 
  }
  
  GravityPoint(GravityPoint gp){
   super(gp.x, gp.y);
   lifetime = gp.lifetime;
  }
  
  GravityPoint(PVector p){
    super(p.x, p.y, p.z);
  }
  
  GravityPoint(float x,float y){
   super(x,y);
  }
}
