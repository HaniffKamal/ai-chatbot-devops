# Haniff Kamal - Audio Deepfake Detection Research

## Problem Statement
The rapid democratization of generative speech synthesis, Voice Conversion (VC), and Text-to-Speech (TTS) models (such as VITS, diffusion models, and neural vocoders) has created severe risks:
- Financial fraud through CEO voice impersonation.
- Social engineering scams bypassing voice biometrics.
- Disinformation and identity theft.

Detecting synthetic speech is inherently challenging because modern neural vocoders generate high-fidelity human speech that is indistinguishable to the human ear.

## Methodology & Feature Engineering
Rather than analyzing raw 1D audio waveforms directly, the research focuses on time-frequency acoustic representations to expose acoustic artifacts left by neural vocoders:
- **Mel-Spectrograms:** Visual representation of frequencies mapped to human auditory perception over time.
- **Constant Q-Transform (CQT):** Geometrically spaced frequency bins that provide high spectral resolution at low frequencies and high temporal resolution at high frequencies.
- **Linear Frequency Cepstral Coefficients (LFCC):** Captures high-frequency spectral cues where neural vocoders often produce phase inconsistencies and unnatural frequency smoothing.

## Model Architectures & Deep Learning
- **Convolutional Neural Networks (CNNs / ResNet):** Modified 2D CNN architectures (ResNet-18, ResNet-34) trained on spectral feature maps to capture subtle spatial patterns and synthetic artifacts.
- **Attention & Temporal Modeling:** Incorporated self-attention layers to analyze long-term temporal dependencies across phoneme transitions.
- **Evaluation Metrics:** Evaluated against benchmark spoofing datasets using Equal Error Rate (EER) and minimum tandem Detection Cost Function (min t-DCF).

## Key Research Takeaways
1. Neural vocoders consistently leave high-frequency phase and spectral continuity anomalies that deep 2D CNNs can reliably detect.
2. Robust data augmentation (Gaussian noise, frequency masking, room acoustic simulation) is critical to prevent the model from overfitting to specific microphone hardware.
3. The ultimate goal is deploying these models as low-latency inference APIs for real-time telecommunications and voice verification security pipelines.
