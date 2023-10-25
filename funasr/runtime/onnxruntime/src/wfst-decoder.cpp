#include <wfst-decoder.h>
namespace funasr {
WfstDecoder::WfstDecoder(fst::Fst<fst::StdArc>* lm,
              PhoneSet* phone_set, Vocab* vocab)
:dec_opts_(), decodable_(dec_opts_.acoustic_scale),
 lm_(lm), phone_set_(phone_set), vocab_(vocab) {
  decoder_ = std::shared_ptr<kaldi::LatticeFasterOnlineDecoder>(
             new kaldi::LatticeFasterOnlineDecoder(*lm_, dec_opts_));
}

WfstDecoder::~WfstDecoder() {
}

void WfstDecoder::StartUtterance() {
  if (decoder_) {
    cur_frame_ = 0;
    cur_token_ = 0;
    decodable_.Reset();
    decoder_->InitDecoding();
  }
}

void WfstDecoder::EndUtterance() {
}

string WfstDecoder::Search(float *in, int len, int64_t token_num) {
  string result;
  if (len == 0) {
    return "";
  }
  std::vector<std::vector<float>> logp_vec;
  int blk_phn_id = phone_set_->GetBlkPhnId();
  for (int i = 0; i < len - 1; i++) {
    std::vector<float> tmp_logp;
    for (int j = 0; j < token_num; j++) {
      tmp_logp.push_back((in + i * token_num)[j]);
    }
    logp_vec.push_back(tmp_logp);
    //insert blank frame
    if (i < len - 2) {
      std::vector<float> blk_logp(token_num, 0.0f);
      blk_logp[blk_phn_id] = MAX_SCORE;
      logp_vec.push_back(blk_logp);
    }
  }
  for (int i = 0; i < logp_vec.size(); i++) {
    cur_frame_++;
    decodable_.AcceptLoglikes(logp_vec[i]);
    decoder_->AdvanceDecoding(&decodable_, 1);
    cur_token_++;
  }
  if (cur_token_ > 0) {
    std::vector<int> words;
    kaldi::Lattice lattice;
    decoder_->GetBestPath(&lattice, false);
    std::vector<int> alignment;
    kaldi::LatticeWeight weight;
    fst::GetLinearSymbolSequence(lattice, &alignment, &words, &weight);
    result = vocab_->Vector2StringV2(words);
  }
  return result;
}

string WfstDecoder::FinalizeDecode() {
  string result;
  if (cur_token_ > 0) {
    std::vector<int> words;
    kaldi::Lattice lattice;
    decodable_.SetFinished();
    decoder_->FinalizeDecoding();
    decoder_->GetBestPath(&lattice, true);
    std::vector<int> alignment;
    kaldi::LatticeWeight weight;
    fst::GetLinearSymbolSequence(lattice, &alignment, &words, &weight);
    result = vocab_->Vector2StringV2(words);
  }
  return result;
}

void WfstDecoder::LoadHwsRes(int inc_bias, unordered_map<string, int> &hws_map) {
  try {
    if (!hws_map.empty()) {
      bias_lm_ = std::make_shared<BiasLm>(hws_map, inc_bias,
                                          *phone_set_, *vocab_);
      decoder_->SetBiasLm(bias_lm_);
    }
  } catch (std::exception const &e) {
        LOG(ERROR) << "Error when load wfst hotwords resource: " << e.what();
        exit(0);
  }
}

void WfstDecoder::UnloadHwsRes() {
  if (bias_lm_) {
    decoder_->ClearBiasLm();
    bias_lm_.reset();
  }
}

} // namespace funasr
