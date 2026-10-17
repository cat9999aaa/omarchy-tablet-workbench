#include <QCoreApplication>
#include <QGeoPositionInfoSource>
#include <QScopedPointer>
#include <QPluginLoader>
#include <QJsonObject>
#include <cstdio>
int main(int argc,char **argv){
 QCoreApplication app(argc,argv);
 if(argc!=2)return 2;
 const auto priority=QPluginLoader(QString::fromLocal8Bit(argv[1])).metaData().value("MetaData").toObject().value("Priority").toInt();
 std::fprintf(stderr,"adapter_priority=%d\n",priority);
 if(priority!=2000)return 2;
 QScopedPointer<QGeoPositionInfoSource> source(QGeoPositionInfoSource::createDefaultSource(nullptr));
 std::fprintf(stderr,"selected=%s\n",source?qPrintable(source->sourceName()):"none");
 return !source||source->sourceName()!=QStringLiteral("pcadmin-gpsd")||source->lastKnownPosition().isValid()?1:0;
}
