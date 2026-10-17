import QtQuick
import QtTest
import org.kde.kirigami as Kirigami
Item {
 width: 400; height: 160
 Kirigami.SearchField { id: search }
 TestCase {
  name: "MapLocale"
  when: windowShown
  function test_fresh_translation() { wait(600); compare(qsTranslate("SearchField","Search…"),"搜索…") }
  function test_search_is_chinese() { wait(600); compare(Qt.locale().name,"zh_CN"); compare(search.placeholderText,"搜索…") }
 }
}
