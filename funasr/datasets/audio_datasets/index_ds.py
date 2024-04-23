import os
import json
import torch
import logging
import concurrent.futures
import librosa
import torch.distributed as dist

from funasr.register import tables


# @tables.register("index_ds_classes", "IndexDSJsonlRankSplit")
# class IndexDSJsonlRankSplit(torch.utils.data.Dataset):
#
#     def __init__(self, path):
#         super().__init__()
#
#         contents = []
#         with open(path, encoding='utf-8') as fin:
#             for line in fin:
#                 data = json.loads(line.strip())
#                 if "text" in data:  # for sft
#                     self.contents.append(data['text'])
#                 if "source" in data:  # for speech lab pretrain
#                     prompt = data["prompt"]
#                     source = data["source"]
#                     target = data["target"]
#                     source_len = data["source_len"]
#                     target_len = data["target_len"]
#
#                     contents.append({"source": source,
#                                      "prompt": prompt,
#                                      "target": target,
#                                      "source_len": source_len,
#                                      "target_len": target_len,
#                                      }
#                                     )
#
#         self.contents = []
#         total_num = len(contents)
#         try:
#             rank = dist.get_rank()
#             world_size = dist.get_world_size()
#         except:
#             rank = 0
#             world_size = 1
#             logging.warning("distributed is not initialized, only single shard")
#         num_per_rank = total_num // world_size
#
#         # rank = 0
#         # import ipdb; ipdb.set_trace()
#         self.contents = contents[rank * num_per_rank:(rank + 1) * num_per_rank]
#
#         logging.info("in rank: {}, num of samplers: {}, total_num of samplers across ranks: {}".format(rank, len(self.contents), len(contents)))
#
#     def __len__(self):
#         return len(self.contents)
#
#     def __getitem__(self, index):
#         try:
#             data = self.contents[index]
#         except:
#             print(index)
#         return data
#
#     def get_source_len(self, data_dict):
#         return data_dict["source_len"]
#
#     def get_target_len(self, data_dict):
#
#         return data_dict["target_len"] if "target_len" in data_dict else 0

@tables.register("index_ds_classes", "IndexDSJsonl")
@tables.register("index_ds_classes", "IndexDSJsonlRankFull")
class IndexDSJsonlRankFull(torch.utils.data.Dataset):
    
    def __init__(self, path: str, **kwargs):
        super().__init__()
        self.max_source_length = kwargs.get("max_source_length", 2048)
        self.min_source_length = kwargs.get("min_source_length", 0)
        self.max_target_length = kwargs.get("max_target_length", 2048)
        self.min_target_length = kwargs.get("min_target_length", 0)
        if isinstance(path, (list, tuple)): # wav.scp, text.txt/text.trans
            from funasr.datasets.audio_datasets.scp2jsonl import gen_jsonl_from_wav_text_list
            jsonl_outdir = os.path.dirname(path[0])
            jsonl_name = "datalist_train.jsonl" if kwargs.get("is_training", True) else "datalist_val.jsonl"
            jsonl_file_out = os.path.join(jsonl_outdir, jsonl_name)
            if not os.path.exists(jsonl_file_out):
                print(f"datalist is: {path}, generate jsonl from it")
                gen_jsonl_from_wav_text_list(path, jsonl_file_out=jsonl_file_out, **kwargs)
            path = jsonl_file_out

        contents = []
        with open(path, encoding='utf-8') as fin:
            for line in fin:
                data = json.loads(line.strip())
                if "text" in data:  # for sft
                    contents.append(data['text'])
                if "source" in data:  # for speech lab pretrain
                    prompt = data.get("prompt", "<ASR>")
                    source = data["source"]
                    target = data["target"]
                    source_len = data.get("source_len", 1)
                    target_len = data.get("target_len", 0)
                    if "aishell" in source:
                        target = target.replace(" ", "")
                    if source_len < self.min_source_length or source_len > self.max_source_length:
                        continue
                    if target_len < self.min_target_length or target_len > self.max_target_length:
                        continue
                    contents_i = {"source": source,
                                 "prompt": prompt,
                                 "target": target,
                                 "source_len": source_len,
                                 "target_len": target_len,
                                 }
                    text_language = data.get("text_language", None)
                    if text_language is not None:
                        contents_i["text_language"] = text_language
                    audio_language = data.get("audio_language", None)
                    if audio_language is not None:
                        contents_i["audio_language"] = audio_language
                    contents.append(contents_i)

        self.contents = contents
        
        logging.info(
            "total_num of samplers across ranks: {}, {}".format(len(self.contents), path))
    
    def __len__(self):
        return len(self.contents)
    
    def __getitem__(self, index):
        try:
            data = self.contents[index]
        except:
            print(index)
        return data
    
    def get_source_len(self, data_dict):
        return data_dict.get("source_len", 1)
    
    def get_target_len(self, data_dict):
        
        return data_dict.get("target_len", 0)


@tables.register("index_ds_classes", "IndexDSJsonlRankSplit")
class IndexDSJsonlRankSplit(torch.utils.data.Dataset):
    
    def __init__(self, path: str, **kwargs):
        super().__init__()
        self.max_source_length = kwargs.get("max_source_length", 2048)
        self.min_source_length = kwargs.get("min_source_length", 0)
        self.max_target_length = kwargs.get("max_target_length", 2048)
        self.min_target_length = kwargs.get("min_target_length", 0)

        with open(path, encoding='utf-8') as fin:
            file_list = fin.readlines()

        total_num = len(file_list)
        try:
            rank = dist.get_rank()
            world_size = dist.get_world_size()
        except:
            rank = 0
            world_size = 1
            logging.warning("distributed is not initialized, only single shard")
        num_per_rank = total_num // world_size
        if num_per_rank * world_size < total_num:
            logging.warning(f"Warning, jsonl file:{total_num} could not be divided by world_size: {world_size}, {path}")

        file_list_rank = file_list[rank * num_per_rank:(rank + 1) * num_per_rank]

        contents = []
        for file_json in file_list_rank:
            
            with open(file_json.strip(), encoding='utf-8') as fin:
                for line in fin:
                    data = json.loads(line.strip())
                    if "text" in data:  # for sft
                        contents.append(data['text'])
                    if "source" in data:  # for speech lab pretrain
                        prompt = data.get("prompt", "<ASR>")
                        source = data["source"].replace("/cpfs01", "/cpfs_speech/data")
                        target = data["target"]
                        source_len = data.get("source_len", 1)
                        target_len = data.get("target_len", 0)
                        
                        if source_len < self.min_source_length or source_len > self.max_source_length:
                            continue
                        if target_len < self.min_target_length or target_len > self.max_target_length:
                            continue
                        contents_i = {"source": source,
                                      "prompt": prompt,
                                      "target": target,
                                      "source_len": source_len,
                                      "target_len": target_len,
                                      }
                        text_language = data.get("text_language", None)
                        if text_language is not None:
                            contents_i["text_language"] = text_language
                        audio_language = data.get("audio_language", None)
                        if audio_language is not None:
                            contents_i["audio_language"] = audio_language
                        contents.append(contents_i)
        
        self.contents = contents
        
        logging.info(f"total_num: {len(self.contents)} of samplers in ranks: {rank}, file_list_rank: {file_list_rank}")
    
    def __len__(self):
        return len(self.contents)
    
    def __getitem__(self, index):
        try:
            data = self.contents[index]
        except:
            print(index)
        return data
    
    def get_source_len(self, data_dict):
        return data_dict.get("source_len", 1)
    
    def get_target_len(self, data_dict):
        
        return data_dict.get("target_len", 0)
