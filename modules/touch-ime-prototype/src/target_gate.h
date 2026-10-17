#pragma once
#include <cstdint>
namespace omt {
inline bool validTarget(uint32_t expected, uint32_t actual, bool focused, bool targetValidationPending = false) {
    return focused && !targetValidationPending && expected != 0 && expected == actual;
}
}
