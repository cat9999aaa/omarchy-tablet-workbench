#include "engine.h"
#include "target_gate.h"
#include <cassert>
#include <iostream>
int main(int argc, char **argv) {
    assert(argc == 3);
    omt::Engine e(argv[1], argv[2]);
    e.mode("t9");
    for (char c : std::string("64426")) e.key(c);
    auto s = e.snapshot();
    bool found = false;
    for (auto &c : s.candidates) if (c == "你好") found = true;
    assert(found && "T9 64426 must contain 你好");
    auto first=s.candidates;
    assert(!s.lastPage);
    e.page(true); s=e.snapshot();
    assert(s.page==1 && s.candidates!=first);
    e.page(false); assert(e.snapshot().page==0);
    e.clear();
    assert(e.snapshot().candidates.empty());
    e.mode("pinyin");
    for (char c : std::string("nihao")) e.key(c);
    s = e.snapshot(); found = false;
    for (auto &c : s.candidates) if (c == "你好") found = true;
    assert(found);
    assert(!e.choose(999).size());
    assert(omt::validTarget(7, 7, true));
    assert(!omt::validTarget(7, 8, true));
    assert(!omt::validTarget(7, 7, false));
    std::cout << "PASS T9, full pinyin, reset, invalid selection and target generation\n";
}
