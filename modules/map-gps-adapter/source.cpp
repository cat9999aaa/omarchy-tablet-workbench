#include "source.h"
#include <QJsonDocument>
#include <QHostAddress>
#include <cmath>
namespace {
bool number(const QJsonObject &d,const char *key,double &v){auto x=d.value(QLatin1String(key));if(!x.isDouble())return false;v=x.toDouble();return std::isfinite(v);}
constexpr int MaxAge=10000,MaxBuffer=65536,MaxLine=16384;
}
QGeoPositionInfo GpsSource::parseFix(const QJsonObject &d,const QDateTime &now){
 double mode,lat,lon;
 if(d.value("class")!="TPV"||!number(d,"mode",mode)||(mode!=2&&mode!=3)||!number(d,"lat",lat)||!number(d,"lon",lon)||lat < -90||lat > 90||lon < -180||lon > 180)return {};
 auto stamp=QDateTime::fromString(d.value("time").toString(),Qt::ISODateWithMs);
 if(!stamp.isValid()||stamp.timeSpec()==Qt::LocalTime||stamp.msecsTo(now)>MaxAge||stamp.msecsTo(now)<-5000)return {};
 QGeoCoordinate coord(lat,lon);double value;
 if(mode==3&&number(d,"altHAE",value))coord.setAltitude(value);
 QGeoPositionInfo result(coord,stamp.toUTC());
 if(number(d,"speed",value)&&value>=0)result.setAttribute(QGeoPositionInfo::GroundSpeed,value);
 if(number(d,"track",value)&&value>=0&&value<360)result.setAttribute(QGeoPositionInfo::Direction,value);
 if(number(d,"eph",value)&&value>=0)result.setAttribute(QGeoPositionInfo::HorizontalAccuracy,value);
 return result;
}
GpsSource::GpsSource(QObject *parent,quint16 testPort):QGeoPositionInfoSource(parent),m_port(testPort){
 m_socket.setReadBufferSize(MaxBuffer+1);
 for(auto *timer:{&m_reconnect,&m_requestDeadline,&m_stale,&m_connectDeadline})timer->setSingleShot(true);
 m_reconnect.setInterval(5000);m_stale.setInterval(MaxAge);m_connectDeadline.setInterval(3000);
 connect(&m_reconnect,&QTimer::timeout,this,&GpsSource::connectLocal);
 connect(&m_connectDeadline,&QTimer::timeout,this,[this]{if(m_socket.state()!=QAbstractSocket::ConnectedState){m_socket.abort();lostConnection();}});
 connect(&m_socket,&QTcpSocket::connected,this,[this]{m_connectDeadline.stop();m_reconnect.stop();m_buffer.clear();m_socket.write("?WATCH={\"enable\":true,\"json\":true};\n");m_stale.start();});
 connect(&m_socket,&QTcpSocket::readyRead,this,&GpsSource::readData);
 connect(&m_socket,&QTcpSocket::disconnected,this,&GpsSource::lostConnection);
 connect(&m_socket,&QTcpSocket::errorOccurred,this,[this](QAbstractSocket::SocketError){lostConnection();});
 connect(&m_requestDeadline,&QTimer::timeout,this,[this]{m_request=false;m_last={};reportError(UpdateTimeoutError);closeIfIdle();});
 connect(&m_stale,&QTimer::timeout,this,[this]{m_last={};if(m_running&&!m_request)reportError(UpdateTimeoutError);});
}
GpsSource::~GpsSource(){m_running=false;m_request=false;m_socket.disconnect(this);m_socket.abort();}
void GpsSource::reportError(Error value){if(m_error==value)return;m_error=value;emit errorOccurred(value);}
void GpsSource::setUpdateInterval(int msec){QGeoPositionInfoSource::setUpdateInterval(msec<=0?0:qMax(minimumUpdateInterval(),msec));}
QGeoPositionInfo GpsSource::lastKnownPosition(bool)const{
 if(!m_age.isValid()||m_age.elapsed()>MaxAge)return {};
 if(!m_last.isValid()||m_last.timestamp().msecsTo(QDateTime::currentDateTimeUtc())>MaxAge)return {};
 return m_last;
}
void GpsSource::connectLocal(){
 if(!wanted()||m_socket.state()!=QAbstractSocket::UnconnectedState)return;
 m_buffer.clear();m_connectDeadline.start();m_socket.connectToHost(QHostAddress::LocalHost,m_port,QIODevice::ReadWrite);
}
void GpsSource::lostConnection(){
 m_connectDeadline.stop();m_buffer.clear();
 if(!wanted())return;
 m_stale.stop();m_last={};reportError(ClosedError);
 if(!m_reconnect.isActive())m_reconnect.start();
}
void GpsSource::closeIfIdle(){if(wanted())return;m_reconnect.stop();m_connectDeadline.stop();m_stale.stop();m_buffer.clear();m_socket.abort();}
void GpsSource::startUpdates(){if(m_running)return;m_running=true;m_error=NoError;m_emitted.invalidate();connectLocal();}
void GpsSource::stopUpdates(){m_running=false;m_last={};closeIfIdle();}
void GpsSource::requestUpdate(int timeout){
 if(m_request)return;
 if(timeout!=0&&timeout<minimumUpdateInterval()){m_error=NoError;reportError(UpdateTimeoutError);return;}
 m_request=true;m_error=NoError;m_requestDeadline.start(timeout==0?10000:timeout);connectLocal();
}
void GpsSource::readData(){
 if(!wanted()){m_socket.readAll();return;}
 m_buffer+=m_socket.readAll();
 if(m_buffer.size()>MaxBuffer){m_socket.abort();lostConnection();return;}
 for(qsizetype end;(end=m_buffer.indexOf('\n'))>=0;){
  auto line=m_buffer.left(end);m_buffer.remove(0,end+1);
  if(line.size()>MaxLine){m_socket.abort();lostConnection();return;}
  auto doc=QJsonDocument::fromJson(line);if(!doc.isObject())continue;auto obj=doc.object();if(obj.value("class")!="TPV")continue;
  auto fix=parseFix(obj,QDateTime::currentDateTimeUtc());
  // gpsd may split one observation over several TPV reports. Partial or
  // malformed reports neither erase a fresh fix nor extend its lifetime.
  if(!fix.isValid()){
   double mode;
   if(number(obj,"mode",mode)&&(mode==0||mode==1)){
    m_last={};
    if(m_running&&!m_request)reportError(UpdateTimeoutError);
   }
   continue;
  }
  m_last=fix;m_age.restart();
  const auto age=qMax<qint64>(0,fix.timestamp().msecsTo(QDateTime::currentDateTimeUtc()));
  m_stale.start(int(qMax<qint64>(1,MaxAge-age)));m_error=NoError;
  const bool deliver=m_request||!m_emitted.isValid()||m_emitted.elapsed()>=qMax(minimumUpdateInterval(),updateInterval());
  if(deliver){m_emitted.restart();if(m_request){m_request=false;m_requestDeadline.stop();}emit positionUpdated(fix);closeIfIdle();}
 }
 if(m_buffer.size()>MaxLine){m_socket.abort();lostConnection();}
}
