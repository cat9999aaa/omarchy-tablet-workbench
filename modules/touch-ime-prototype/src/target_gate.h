#pragma once
#include <cstdint>
namespace omt {
inline bool validTarget(uint32_t expected, uint32_t actual, bool focused) {
    return focused && expected != 0 && expected == actual;
}
}
