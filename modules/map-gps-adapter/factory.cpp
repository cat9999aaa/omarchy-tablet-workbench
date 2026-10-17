#include <QGeoPositionInfoSourceFactory>
#include "source.h"
class Factory final:public QObject,public QGeoPositionInfoSourceFactory {
 Q_OBJECT
 Q_PLUGIN_METADATA(IID "org.qt-project.qt.position.sourcefactory/6.0" FILE "metadata.json")
 Q_INTERFACES(QGeoPositionInfoSourceFactory)
public:
 QGeoPositionInfoSource *positionInfoSource(QObject *parent,const QVariantMap &) override{return new GpsSource(parent);}
 QGeoSatelliteInfoSource *satelliteInfoSource(QObject *,const QVariantMap &) override{return nullptr;}
 QGeoAreaMonitorSource *areaMonitor(QObject *,const QVariantMap &) override{return nullptr;}
};
#include "factory.moc"
