#include "engine.h"
#include <cassert>
#include <string>
int main(int argc,char **argv){assert(argc==4);omt::Engine e(argv[1],argv[2]);e.setLearning(std::string(argv[3])=="on");e.mode("pinyin");for(char c:std::string("nihao"))e.key(c);auto s=e.snapshot();bool found=false;for(size_t i=0;i<s.candidates.size();i++)if(s.candidates[i]=="你好"){assert(e.choose(i)=="你好");found=true;break;}assert(found);assert(e.backupDictionary());}
