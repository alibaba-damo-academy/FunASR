import copy
import logging
from typing import Optional
from typing import Tuple
from typing import Union

import humanfriendly
import numpy as np
import torch
from pathlib import Path
from torch_complex.tensor import ComplexTensor
from typeguard import check_argument_types

from funasr.layers.log_mel import LogMel
from funasr.layers.stft import Stft
from funasr.models.frontend.abs_frontend import AbsFrontend
from funasr.modules.frontends.frontend import Frontend
from funasr.utils.get_default_kwargs import get_default_kwargs
from funasr.modules.nets_utils import make_pad_mask


class DefaultFrontend(AbsFrontend):
    """Conventional frontend structure for ASR.
    Stft -> WPE -> MVDR-Beamformer -> Power-spec -> Mel-Fbank -> CMVN
    """
    def __init__(
            self,
            fs: Union[int, str] = 16000,
            n_fft: int = 512,
            win_length: int = None,
            hop_length: int = 128,
            window: Optional[str] = "hann",
            center: bool = True,
            normalized: bool = False,
            onesided: bool = True,
            n_mels: int = 80,
            fmin: int = None,
            fmax: int = None,
            htk: bool = False,
            frontend_conf: Optional[dict] = get_default_kwargs(Frontend),
            apply_stft: bool = True,
            use_channel: int = None,
    ):
        assert check_argument_types()
        super().__init__()
        if isinstance(fs, str):
            fs = humanfriendly.parse_size(fs)

        # Deepcopy (In general, dict shouldn't be used as default arg)
        frontend_conf = copy.deepcopy(frontend_conf)
        self.hop_length = hop_length

        if apply_stft:
            self.stft = Stft(
                n_fft=n_fft,
                win_length=win_length,
                hop_length=hop_length,
                center=center,
                window=window,
                normalized=normalized,
                onesided=onesided,
            )
        else:
            self.stft = None
        self.apply_stft = apply_stft

        if frontend_conf is not None:
            self.frontend = Frontend(idim=n_fft // 2 + 1, **frontend_conf)
        else:
            self.frontend = None

        self.logmel = LogMel(
            fs=fs,
            n_fft=n_fft,
            n_mels=n_mels,
            fmin=fmin,
            fmax=fmax,
            htk=htk,
        )
        self.n_mels = n_mels
        self.frontend_type = "default"
        self.use_channel = use_channel

    def output_size(self) -> int:
        return self.n_mels

    def forward(
            self, input: torch.Tensor, input_lengths: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # 1. Domain-conversion: e.g. Stft: time -> time-freq
        if self.stft is not None:
            input_stft, feats_lens = self._compute_stft(input, input_lengths)
        else:
            input_stft = ComplexTensor(input[..., 0], input[..., 1])
            feats_lens = input_lengths
        # 2. [Option] Speech enhancement
        if self.frontend is not None:
            assert isinstance(input_stft, ComplexTensor), type(input_stft)
            # input_stft: (Batch, Length, [Channel], Freq)
            input_stft, _, mask = self.frontend(input_stft, feats_lens)

        # 3. [Multi channel case]: Select a channel
        if input_stft.dim() == 4:
            # h: (B, T, C, F) -> h: (B, T, F)
            if self.training:
                if self.use_channel is not None:
                    input_stft = input_stft[:, :, self.use_channel, :]
                else:
                    # Select 1ch randomly
                    ch = np.random.randint(input_stft.size(2))
                    input_stft = input_stft[:, :, ch, :]
            else:
                # Use the first channel
                input_stft = input_stft[:, :, 0, :]

        # 4. STFT -> Power spectrum
        # h: ComplexTensor(B, T, F) -> torch.Tensor(B, T, F)
        input_power = input_stft.real ** 2 + input_stft.imag ** 2

        # 5. Feature transform e.g. Stft -> Log-Mel-Fbank
        # input_power: (Batch, [Channel,] Length, Freq)
        #       -> input_feats: (Batch, Length, Dim)
        input_feats, _ = self.logmel(input_power, feats_lens)
        return input_feats, feats_lens

    def _compute_stft(
            self, input: torch.Tensor, input_lengths: torch.Tensor
    ) -> torch.Tensor:
        input_stft, feats_lens = self.stft(input, input_lengths)

        assert input_stft.dim() >= 4, input_stft.shape
        # "2" refers to the real/imag parts of Complex
        assert input_stft.shape[-1] == 2, input_stft.shape

        # Change torch.Tensor to ComplexTensor
        # input_stft: (..., F, 2) -> (..., F)
        input_stft = ComplexTensor(input_stft[..., 0], input_stft[..., 1])
        return input_stft, feats_lens


class MultiChannelFrontend(AbsFrontend):
    """Conventional frontend structure for ASR.
    Stft -> WPE -> MVDR-Beamformer -> Power-spec -> Mel-Fbank -> CMVN
    """

    def __init__(
            self,
            fs: Union[int, str] = 16000,
            n_fft: int = 400,
            frame_length: int = 25,
            frame_shift: int = 10,
            window: Optional[str] = "hann",
            center: bool = True,
            normalized: bool = False,
            onesided: bool = True,
            n_mels: int = 80,
            fmin: int = None,
            fmax: int = None,
            htk: bool = False,
            frontend_conf: Optional[dict] = get_default_kwargs(Frontend),
            apply_stft: bool = True,
            use_channel: int = None,
            lfr_m: int = 1,
            lfr_n: int = 1,
            cmvn_file: str = None
    ):
        assert check_argument_types()
        super().__init__()
        if isinstance(fs, str):
            fs = humanfriendly.parse_size(fs)

        # Deepcopy (In general, dict shouldn't be used as default arg)
        frontend_conf = copy.deepcopy(frontend_conf)
        self.win_length = frame_length * 16
        self.hop_length = frame_shift * 16

        if apply_stft:
            self.stft = Stft(
                n_fft=n_fft,
                win_length=self.win_length,
                hop_length=self.hop_length,
                center=center,
                window=window,
                normalized=normalized,
                onesided=onesided,
            )
        else:
            self.stft = None
        self.apply_stft = apply_stft

        if frontend_conf is not None:
            self.frontend = Frontend(idim=n_fft // 2 + 1, **frontend_conf)
        else:
            self.frontend = None

        self.logmel = LogMel(
            fs=fs,
            n_fft=n_fft,
            n_mels=n_mels,
            fmin=fmin,
            fmax=fmax,
            htk=htk,
        )
        self.n_mels = n_mels
        self.frontend_type = "default"
        self.use_channel = use_channel
        if self.use_channel is not None:
            logging.info("use the channel %d" % (self.use_channel))
        else:
            logging.info("random select channel")
        self.cmvn_file = cmvn_file
        if self.cmvn_file is not None:
            mean, std = self._load_cmvn(self.cmvn_file)
            self.register_buffer("mean", torch.from_numpy(mean))
            self.register_buffer("std", torch.from_numpy(std))

    def output_size(self) -> int:
        return self.n_mels

    def forward(
            self, input: torch.Tensor, input_lengths: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        # 1. Domain-conversion: e.g. Stft: time -> time-freq
        if self.stft is not None:
            input_stft, feats_lens = self._compute_stft(input, input_lengths)
        else:
            input_stft = ComplexTensor(input[..., 0], input[..., 1])
            feats_lens = input_lengths
        # 2. [Option] Speech enhancement
        if self.frontend is not None:
            assert isinstance(input_stft, ComplexTensor), type(input_stft)
            # input_stft: (Batch, Length, [Channel], Freq)
            input_stft, _, mask = self.frontend(input_stft, feats_lens)

        # 3. [Multi channel case]: Select a channel
        if input_stft.dim() == 4:
            # h: (B, T, C, F) -> h: (B, T, F)
            if self.training:
                if self.use_channel is not None:
                    input_stft = input_stft[:, :, self.use_channel, :]
                    
                else:
                    # Select 1ch randomly
                    ch = np.random.randint(input_stft.size(2))
                    input_stft = input_stft[:, :, ch, :]
            else:
                # Use the first channel
                input_stft = input_stft[:, :, 0, :]

        # 4. STFT -> Power spectrum
        # h: ComplexTensor(B, T, F) -> torch.Tensor(B, T, F)
        input_power = input_stft.real ** 2 + input_stft.imag ** 2

        # 5. Feature transform e.g. Stft -> Log-Mel-Fbank
        # input_power: (Batch, [Channel,] Length, Freq)
        #       -> input_feats: (Batch, Length, Dim)
        input_feats, _ = self.logmel(input_power, feats_lens)
        
        # 6. Apply CMVN
        if self.cmvn_file is not None:
            if feats_lens is None:
                feats_lens = input_feats.new_full([input_feats.size(0)], input_feats.size(1))
            self.mean = self.mean.to(input_feats.device, input_feats.dtype)
            self.std = self.std.to(input_feats.device, input_feats.dtype)
            mask = make_pad_mask(feats_lens, input_feats, 1)

            if input_feats.requires_grad:
                input_feats = input_feats + self.mean
            else:
                input_feats += self.mean
            if input_feats.requires_grad:
                input_feats = input_feats.masked_fill(mask, 0.0)
            else:
                input_feats.masked_fill_(mask, 0.0)

            input_feats *= self.std

        return input_feats, feats_lens

    def _compute_stft(
            self, input: torch.Tensor, input_lengths: torch.Tensor
    ) -> torch.Tensor:
        input_stft, feats_lens = self.stft(input, input_lengths)

        assert input_stft.dim() >= 4, input_stft.shape
        # "2" refers to the real/imag parts of Complex
        assert input_stft.shape[-1] == 2, input_stft.shape

        # Change torch.Tensor to ComplexTensor
        # input_stft: (..., F, 2) -> (..., F)
        input_stft = ComplexTensor(input_stft[..., 0], input_stft[..., 1])
        return input_stft, feats_lens

    def _load_cmvn(self, cmvn_file):
        with open(cmvn_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        means_list = []
        vars_list = []
        for i in range(len(lines)):
            line_item = lines[i].split()
            if line_item[0] == '<AddShift>':
                line_item = lines[i + 1].split()
                if line_item[0] == '<LearnRateCoef>':
                    add_shift_line = line_item[3:(len(line_item) - 1)]
                    means_list = list(add_shift_line)
                    continue
            elif line_item[0] == '<Rescale>':
                line_item = lines[i + 1].split()
                if line_item[0] == '<LearnRateCoef>':
                    rescale_line = line_item[3:(len(line_item) - 1)]
                    vars_list = list(rescale_line)
                    continue
        means = np.array(means_list).astype(np.float)
        vars = np.array(vars_list).astype(np.float)
        return means, vars