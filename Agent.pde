int currentSizeContour = 0;


class Agent{
  List<PVector> vectors;
  List<Integer> vectorsClass;
  boolean changed=false;
  
  Agent(){
    this.vectors=new ArrayList<PVector>();  
    this.vectorsClass=new ArrayList<Integer>();  
  }
  
  //Crea i nuovi cluster sotto forma di vettori
  List<PVector> reasoning(OscMessage msg){
    List<PVector> vectorList = null;
    
    int size = msg.get(0).intValue();
    if(size > 0){
      vectorList = new ArrayList<PVector>();
      for(int i = 1; i < size * 2; i = i + 2){
          vectorList.add(new PVector(msg.get(i).floatValue(), msg.get(i + 1).floatValue()));
      }
    }
    return vectorList;
  }
  
  //Avvia il processo di clusterizzazione sul server,
  // inviando pacchetti contenenti le informazioni 
  //riguardanti le posizioni dei pixel di movimento
  void action(List<PVector> list){  
    //if(this.changed){ // send OSC message
      //println("Sending message: vectors " + list.size());
      OscMessage msg = null; 
      int offset = 1;
      
      if(list.size() > 1000){
         offset += list.size() / 1000; 
         println("Resizing " + offset);
      }

      //invio dei messaggi
      for (int i=0; i< list.size(); i = min(i + offset, list.size())){
        msg = new OscMessage("/cluster"); 
        //Escludo i pixel di contorno
        if(list.get(i).x == 0 || list.get(i).y == 0 || 
            list.get(i).x == width || list.get(i).y == height){
            continue;
        }else{
          msg.add(list.get(i).x);
          msg.add(list.get(i).y);
        }
       
        oscP5.send(msg, location);
      }
    
    //Invio messaggio di stop stream
    msg = new OscMessage("/cluster");
    oscP5.send(msg.add("STOP"), location); 
  }
  
  List<PVector> getContour(){
    return vectors;  
  }
  
  List<Integer> getClasses(){
    return vectorsClass;  
  }
}
