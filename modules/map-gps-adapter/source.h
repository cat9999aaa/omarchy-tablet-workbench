#pragma once
#include <QGeoPositionInfoSource>
#include <QTcpSocket>
#include <QTimer>
#include <QElapsedTimer>
#include <QJsonObject>
// One application-owned subscriber; the existing gpsd remains device owner.
class GpsSource final:public QGeoPositionInfoSource {
 Q_OBJECT
public:
 explicit GpsSource(QObject *parent=nullptr,quint16 testPort=2947);
 ~GpsSource() override;
 static QGeoPositionInfo parseFix(const QJsonObject &object,const QDateTime &now);
 QGeoPositionInfo lastKnownPosition(bool satelliteOnly=false) const override;
 PositioningMethods supportedPositioningMethods() const override{return SatellitePositioningMethods;}
 int minimumUpdateInterval() const override{return 1000;}
 Error error() const override{return m_error;}
 void setUpdateInterval(int msec) override;
 void startUpdates() override;
 void stopUpdates() override;
 void requestUpdate(int timeout=0) override;
private:
 void connectLocal();void readData();void reportError(Error);void lostConnection();void closeIfIdle();
 bool wanted() const{return m_running||m_request;}
 QTcpSocket m_socket;
 QTimer m_reconnect,m_requestDeadline,m_stale,m_connectDeadline;
 quint16 m_port;bool m_running=false,m_request=false;
 Error m_error=NoError;QByteArray m_buffer;QGeoPositionInfo m_last;
 QElapsedTimer m_age,m_emitted;
};
