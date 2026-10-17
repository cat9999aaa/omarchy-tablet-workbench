#include <QtTest>
#include <QTcpServer>
#include <QTcpSocket>
#include <QJsonDocument>
#include <QSignalSpy>
#include "source.h"
class Tests:public QObject {
 Q_OBJECT
 QJsonObject fix(int mode=2) {return {{"class","TPV"},{"mode",mode},{"lat",10.0},{"lon",20.0},{"time",QDateTime::currentDateTimeUtc().toString(Qt::ISODateWithMs)}};}
private slots:
 void valid2D3D() {
  auto d=fix();auto p=GpsSource::parseFix(d,QDateTime::currentDateTimeUtc());QVERIFY(p.isValid());QCOMPARE(p.coordinate().type(),QGeoCoordinate::Coordinate2D);
  d=fix(3);d["altHAE"]=123.5;d["speed"]=1.25;d["track"]=90.0;d["eph"]=3.0;
  p=GpsSource::parseFix(d,QDateTime::currentDateTimeUtc());QVERIFY(p.isValid());QCOMPARE(p.coordinate().altitude(),123.5);QCOMPARE(p.attribute(QGeoPositionInfo::GroundSpeed),1.25);QCOMPARE(p.attribute(QGeoPositionInfo::HorizontalAccuracy),3.0);
 }
 void invalidFixes() {
  const QList<QPair<QString,QJsonValue>> bad={{"class","SKY"},{"mode",1},{"mode",2.5},{"lat",91},{"lon",181},{"lat","10"},{"lon",true},{"time","garbage"},{"time",QDateTime::currentDateTimeUtc().addSecs(-60).toString(Qt::ISODateWithMs)},{"time",QDateTime::currentDateTimeUtc().addSecs(60).toString(Qt::ISODateWithMs)}};
  for(const auto &change:bad){auto d=fix();d[change.first]=change.second;QVERIFY(!GpsSource::parseFix(d,QDateTime::currentDateTimeUtc()).isValid());}
  auto d=fix();d.remove("time");QVERIFY(!GpsSource::parseFix(d,QDateTime::currentDateTimeUtc()).isValid());
 }
 void streamAndStop() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);
  source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());QTRY_VERIFY(peer->bytesAvailable()>0);
  auto watch=peer->readAll();QVERIFY(watch.contains("WATCH"));QVERIFY(!watch.contains("device"));
  peer->write("garbage\n");peer->write(QJsonDocument(fix()).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);QVERIFY(source.lastKnownPosition().isValid());
  source.stopUpdates();QTRY_COMPARE(peer->state(),QAbstractSocket::UnconnectedState);QVERIFY(!source.lastKnownPosition().isValid());
 }
 void fragmentedAndLostFix() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());
  auto raw=QJsonDocument(fix()).toJson(QJsonDocument::Compact);peer->write(raw.left(12));peer->flush();QTest::qWait(15);QCOMPARE(fixes.count(),0);peer->write(raw.mid(12)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);
  peer->write(QJsonDocument(fix(1)).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_VERIFY(!source.lastKnownPosition().isValid());source.stopUpdates();
 }
 void disconnectAndOversize() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->write(QJsonDocument(fix()).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);
  peer->write(QByteArray(70000,'x'));peer->flush();QTRY_COMPARE(peer->state(),QAbstractSocket::UnconnectedState);QVERIFY(!source.lastKnownPosition().isValid());source.stopUpdates();
 }
 void singleRequestAndTimeout() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy errors(&source,&QGeoPositionInfoSource::errorOccurred);source.requestUpdate(30);QTRY_VERIFY_WITH_TIMEOUT(errors.count()>0,500);QCOMPARE(source.error(),QGeoPositionInfoSource::UpdateTimeoutError);source.stopUpdates();
  GpsSource success(nullptr,server.serverPort());QSignalSpy fixes(&success,&QGeoPositionInfoSource::positionUpdated);while(server.hasPendingConnections())delete server.nextPendingConnection();success.requestUpdate(1000);QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->write(QJsonDocument(fix()).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);QTRY_COMPARE(peer->state(),QAbstractSocket::UnconnectedState);
 }
 void partialReportKeepsFreshFix() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);QSignalSpy errors(&source,&QGeoPositionInfoSource::errorOccurred);source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->write(QJsonDocument(fix(3)).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);
  QJsonObject partial{{"class","TPV"},{"mode",3},{"speed",1.0}};peer->write(QJsonDocument(partial).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTest::qWait(50);QVERIFY(source.lastKnownPosition().isValid());QCOMPARE(errors.count(),0);source.stopUpdates();
 }
 void expiresWithoutNewFix() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);QSignalSpy errors(&source,&QGeoPositionInfoSource::errorOccurred);source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());
  auto d=fix();d["time"]=QDateTime::currentDateTimeUtc().addMSecs(-9000).toString(Qt::ISODateWithMs);peer->write(QJsonDocument(d).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);QVERIFY(source.lastKnownPosition().isValid());QTRY_VERIFY_WITH_TIMEOUT(!source.lastKnownPosition().isValid(),1500);QTRY_COMPARE_WITH_TIMEOUT(errors.count(),1,300);source.stopUpdates();
 }
 void stopDoesNotCancelSingleRequest() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);source.startUpdates();source.requestUpdate(1000);source.stopUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->write(QJsonDocument(fix()).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);QTRY_COMPARE(peer->state(),QAbstractSocket::UnconnectedState);
 }
 void shortRequestDoesNotConnect() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy errors(&source,&QGeoPositionInfoSource::errorOccurred);source.requestUpdate(10);QCOMPARE(errors.count(),1);QCOMPARE(source.error(),QGeoPositionInfoSource::UpdateTimeoutError);QTest::qWait(30);QVERIFY(!server.hasPendingConnections());
 }
 void requestWaitsForFixOrDeadline() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());QSignalSpy errors(&source,&QGeoPositionInfoSource::errorOccurred);QSignalSpy fixes(&source,&QGeoPositionInfoSource::positionUpdated);source.requestUpdate(1200);QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->write(QJsonDocument(fix(1)).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTest::qWait(40);QCOMPARE(errors.count(),0);peer->write(QJsonDocument(fix()).toJson(QJsonDocument::Compact)+"\n");peer->flush();QTRY_COMPARE(fixes.count(),1);QCOMPARE(errors.count(),0);
  source.requestUpdate(1000);QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> again(server.nextPendingConnection());again->write(QJsonDocument(fix(1)).toJson(QJsonDocument::Compact)+"\n");again->flush();QTest::qWait(40);QCOMPARE(errors.count(),0);QTRY_COMPARE_WITH_TIMEOUT(errors.count(),1,1500);QCOMPARE(fixes.count(),1);QTest::qWait(30);QCOMPARE(errors.count(),1);
 }
 void reconnectAndCancelBackoff() {
  QTcpServer server;QVERIFY(server.listen(QHostAddress::LocalHost));GpsSource source(nullptr,server.serverPort());source.startUpdates();QTRY_VERIFY(server.hasPendingConnections());QScopedPointer<QTcpSocket> peer(server.nextPendingConnection());peer->disconnectFromHost();QTRY_COMPARE(peer->state(),QAbstractSocket::UnconnectedState);QTest::qWait(100);QVERIFY(!server.hasPendingConnections());QTRY_VERIFY_WITH_TIMEOUT(server.hasPendingConnections(),5500);QScopedPointer<QTcpSocket> again(server.nextPendingConnection());again->disconnectFromHost();QTRY_COMPARE(again->state(),QAbstractSocket::UnconnectedState);source.stopUpdates();QTest::qWait(5200);QVERIFY(!server.hasPendingConnections());
 }
 void intervalAndMethods() {GpsSource source;source.setUpdateInterval(10);QCOMPARE(source.updateInterval(),1000);QCOMPARE(source.supportedPositioningMethods(),QGeoPositionInfoSource::SatellitePositioningMethods);}

};
QTEST_GUILESS_MAIN(Tests)
#include "tests.moc"
