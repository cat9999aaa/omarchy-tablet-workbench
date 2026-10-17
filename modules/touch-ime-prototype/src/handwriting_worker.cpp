#include <metasequoia/handwriting.h>
#include <QCoreApplication>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <iostream>
int main(int argc,char **argv){
 QCoreApplication app(argc,argv);if(argc!=2)return 2;
 try {
  metasequoia::handwriting::Recognizer engine(argv[1]);
  std::string line;
  while(std::getline(std::cin,line)){
   QJsonObject out;auto in=QJsonDocument::fromJson(QByteArray::fromStdString(line)).object();out["revision"]=in.value("revision");
   try {
    if(line.size()>65536)throw std::invalid_argument("limit");
    std::vector<metasequoia::handwriting::Stroke> strokes;
    for(auto entry:in.value("strokes").toArray()){
     metasequoia::handwriting::Stroke stroke;
     for(auto value:entry.toArray()){auto p=value.toObject();if(!p.value("x").isDouble()||!p.value("y").isDouble())throw std::invalid_argument("point");stroke.push_back({float(p["x"].toDouble()),float(p["y"].toDouble())});}
     strokes.push_back(std::move(stroke));
    }
    auto result=engine.recognize(strokes,float(in["width"].toDouble()),float(in["height"].toDouble()));QJsonArray candidates;
    for(size_t i=0;i<result.size()&&i<6;i++)candidates.append(QString::fromStdString(result[i]));out["candidates"]=candidates;
   }catch(const std::exception&){out["error"]="手写笔画无效，请重写";}
   std::cout<<QJsonDocument(out).toJson(QJsonDocument::Compact).constData()<<'\n'<<std::flush;
  }
 }catch(const std::exception&){return 1;}return 0;
}
