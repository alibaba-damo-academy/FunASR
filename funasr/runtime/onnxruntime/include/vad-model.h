
#ifndef VAD_MODEL_H
#define VAD_MODEL_H

#include <string>
#include <map>
#include <vector>

namespace funasr {
class VadModel {
  public:
    virtual ~VadModel(){};
    virtual void InitVad(const std::string &vad_model, const std::string &vad_cmvn, const std::string &vad_config, int thread_num)=0;
    virtual std::vector<std::vector<int>> Infer(std::vector<float> &waves, bool input_finished=true)=0;
    virtual void ReadModel(const char* vad_model)=0;
    virtual void LoadConfigFromYaml(const char* filename)=0;
    virtual void FbankKaldi(float sample_rate, std::vector<std::vector<float>> &vad_feats,
                    std::vector<float> &waves)=0;
    virtual void LoadCmvn(const char *filename)=0;
    virtual void InitCache()=0;
};

VadModel *CreateVadModel(std::map<std::string, std::string>& model_path, int thread_num, int mode);
} // namespace funasr
#endif
