#pragma once
#include <rime_api.h>
// Rime's C API macro collides with Qt's metatype enumerator.
#undef Bool
#include <string>
#include <vector>
namespace omt {
struct Snapshot { std::string preedit; std::vector<std::string> candidates; int page=0; bool lastPage=true; };
class Engine {
    RimeApi *api_ = nullptr;
    RimeSessionId session_ = 0;
    std::string user_;
    std::string mode_ = "t9";
    bool learning_ = true;
public:
    Engine(const std::string &data, const std::string &user);
    ~Engine();
    Engine(const Engine &) = delete;
    void setLearning(bool enabled);
    bool backupDictionary();
    bool forgetCandidate(size_t index);
    void mode(const std::string &name);
    bool key(int code);
    std::string takeCommit();
    std::string choose(size_t index);
    void clear();
    void page(bool next);
    Snapshot snapshot();
};
}
