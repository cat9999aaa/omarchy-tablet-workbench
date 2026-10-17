#include "engine.h"
#include <cstring>
#include <filesystem>
#include <stdexcept>
#include <sys/stat.h>
namespace omt {
Engine::Engine(const std::string &data, const std::string &user) : user_(user) {
    namespace fs = std::filesystem;
    fs::create_directories(user_);
    chmod(user_.c_str(), 0700);
    fs::copy_file("/usr/share/rime-data/default.yaml", fs::path(user_)/"default.yaml", fs::copy_options::overwrite_existing);
    for (auto name : {"omt_t9.schema.yaml", "omt_full.schema.yaml", "default.custom.yaml", "omt_t9_private.schema.yaml", "omt_full_private.schema.yaml"}) {
        fs::copy_file(fs::path(data)/name, fs::path(user_)/name, fs::copy_options::overwrite_existing);
    }
    api_ = rime_get_api();
    RIME_STRUCT(RimeTraits, traits);
    traits.shared_data_dir = "/usr/share/rime-data";
    traits.user_data_dir = user_.c_str();
    traits.distribution_name = "Omarchy Touch IME";
    traits.distribution_code_name = "omt";
    traits.distribution_version = "0.1.0";
    traits.app_name = "rime.omt";
    traits.min_log_level = 2;
    traits.log_dir = "";
    api_->setup(&traits);
    api_->initialize(&traits);
    if (api_->start_maintenance(False)) api_->join_maintenance_thread();
    session_ = api_->create_session();
    if (!session_) throw std::runtime_error("Cannot create Rime session");
    mode("t9");
}
Engine::~Engine() { if (session_) api_->destroy_session(session_); if (api_) api_->finalize(); }
void Engine::mode(const std::string &name) {
    clear();
    mode_ = name;
    auto schema = std::string(name == "t9" ? "omt_t9" : "omt_full") + (learning_ ? "" : "_private");
    if (!api_->select_schema(session_, schema.c_str()))
        throw std::runtime_error("Cannot select input schema");
    api_->set_option(session_, "simplification", True);
    api_->set_option(session_, "ascii_mode", False);
}
void Engine::setLearning(bool enabled) { learning_=enabled;mode(mode_); }
bool Engine::forgetCandidate(size_t index) { if(index>=snapshot().candidates.size())return false;return api_->delete_candidate_on_current_page(session_,index); }
bool Engine::backupDictionary() {
    bool synced = api_->sync_user_data();
    api_->join_maintenance_thread();
    // User-data sync invalidates Rime sessions. Restore the input session
    // before the next focus change or schema switch uses it.
    if (!api_->find_session(session_)) {
        session_ = api_->create_session();
        if (!session_) throw std::runtime_error("Cannot recreate Rime session after sync");
        mode(mode_);
    }
    return synced;
}
bool Engine::key(int code) { return api_->process_key(session_, code, 0); }
void Engine::clear() { if (session_) api_->clear_composition(session_); }
void Engine::page(bool next) { api_->process_key(session_, next ? 0xff56 : 0xff55, 0); }
std::string Engine::takeCommit() {
    RIME_STRUCT(RimeCommit, commit);
    if (!api_->get_commit(session_, &commit)) return {};
    std::string text = commit.text ? commit.text : "";
    api_->free_commit(&commit); return text;
}
std::string Engine::choose(size_t index) {
    auto state = snapshot();
    if (index >= state.candidates.size()) return {};
    api_->select_candidate_on_current_page(session_, index);
    return takeCommit();
}
Snapshot Engine::snapshot() {
    Snapshot s; RIME_STRUCT(RimeContext, ctx);
    if (api_->get_context(session_, &ctx)) {
        s.page=ctx.menu.page_no; s.lastPage=ctx.menu.is_last_page;
        s.preedit = ctx.composition.preedit ? ctx.composition.preedit : "";
        for (int i=0; i<ctx.menu.num_candidates; ++i) s.candidates.emplace_back(ctx.menu.candidates[i].text);
        api_->free_context(&ctx);
    }
    return s;
}
}
