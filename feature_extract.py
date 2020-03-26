import os
import sys
import librosa 
import numpy as np
from multiprocessing import Pool
import argparse

import damp_config as config 

N_WORKERS = 5 

def parallel_mel(audiofile, save_dir):
    savefile = os.path.join(save_dir, audiofile.stem + '.npy')
    
    if not os.path.exists(os.path.dirname(savefile)):
        os.makedirs(os.path.dirname(savefile), exist_ok=True)

    if os.path.exists(savefile):
        print (savefile, ":already exists")
        return
    
    try : 
        y, _ = librosa.load(audiofile)
    except : 
        e = sys.exc_info()[0]
        print (audiofile, ":unable to load", e)
        return 
    S = librosa.core.stft(y, n_fft=config.n_fft, hop_length=config.hop_length)
    X = np.abs(S)
    mel_basis = librosa.filters.mel(sr=config.sr, n_fft=config.n_fft, n_mels=config.n_mels)
    mel_S = np.dot(mel_basis, X)
    mel_S = np.log10(1+10*mel_S)
    mel_S = mel_S.astype(np.float32)
    print (mel_S.shape, savefile)
    np.save(savefile,  mel_S)

 

def process_msd_singer():
    import msd_config 
    global N_WORKERS 

    data_dir = msd_config.data_dir
    save_dir = msd_config.mel_dir 
    audio_dir = msd_config.audio_dir
    ext = '.mp3' # .wav for ss .mp3 for mix 

    #### training data 
    x_train, x_valid, x_test = np.load(os.path.join(config.data_dir, 'generator_dcnn_train_data_1000_d.npy'))

    all_tracks = [] 
    for track in x_train:
        all_tracks.append((track[1].replace('.npy', ext), audio_dir, save_dir, ext))

    for track in x_valid:
        all_tracks.append((track[1].replace('.npy', ext), audio_dir, save_dir, ext))

    for track in x_test:
        all_tracks.append((track[1].replace('.npy', ext), audio_dir, save_dir, ext))

    print (len(all_tracks))

    all_tracks = [(all_tracks[i]) for i in range(len(all_tracks))]

    with Pool(N_WORKERS) as p:
        p.starmap(parallel_mel, all_tracks)
    
    print ("training data done")

    del all_tracks

    #### testing data 
    x_unseen_train, x_unseen_test = np.load(os.path.join(config.data_dir, 'gen_dcnn_unseen_data_500_d.npy'))
    
    all_tracks = [] 
    for track in x_train:
        all_tracks.append(track[1].replace('.npy', ext), audio_dir, save_dir, ext)

    for track in x_test:
        all_tracks.append(track[1].replace('.npy', ext), audio_dir, save_dir, ext)

    all_tracks = [(all_tracks[i]) for i in range(len(all_tracks))]

    with Pool(N_WORKERS) as p:
        p.starmap(parallel_mel, all_tracks)
       
    print ("testing data done") 
    del x_unseen_train, x_unseen_test, all_tracks
    

    print ("computing mean, std...")
    all_mels = [] 
    for track in x_train : 
        artist_id, feat_path, start_frame = track 
        feat = np.load(config.mel_path + feat_path.replace(ext, '.npy'))[:, start_frame : start_frame + config.input_frame_len]
        all_mels.append(feat)

    print ("mean:",np.mean(all_mels), "std:", np.std(all_mels))



def process_damp(audio_dir, mel_dir, ext):
    import damp_config 
    from utils import load_data_segment
    global N_WORKERS 

    train_artists = np.load(os.path.join(damp_config.data_dir, 'artist_1000.npy'))
    train_list, _ = load_data_segment(os.path.join(damp_config.data_dir, 'train_artist_track_1000.pkl'), train_artists)
    valid_list, _ = load_data_segment(os.path.join(damp_config.data_dir, 'valid_artist_track_1000.pkl'), train_artists)

    unseen_train_artists = np.load(os.path.join(damp_config.data_dir, 'unseen_artist_300_2.npy'))
    unseen_train_list, _ = load_data_segment(os.path.join(damp_config.data_dir, 'unseen_model_artist_track_300_2.pkl'), unseen_train_artists)
    unseen_valid_list, _ = load_data_segment(os.path.join(damp_config.data_dir, 'unseen_eval_artist_track_300_2.pkl'), unseen_train_artists)
    
    all_tracks = set()
    for i in range(len(train_list)):
        _, feat_path, _ = train_list[i]
        feat_path = feat_path.replace('.npy', ext)
        all_tracks.add((feat_path, audio_dir, mel_dir, ext))
    for i in range(len(valid_list)):
        _, feat_path, _ = valid_list[i]
        feat_path = feat_path.replace('.npy',ext)
        all_tracks.add((feat_path, audio_dir, mel_dir, ext))

    all_tracks = list(all_tracks)
    print (len(all_tracks))
    
    if not os.path.exists(mel_dir):
        os.makedirs(mel_dir)

    with Pool(N_WORKERS) as p:
        p.starmap(parallel_mel, all_tracks)
    

    all_tracks = set()
    for i in range(len(unseen_train_list)):
        _, feat_path, _ = unseen_train_list[i]
        feat_path =feat_path.replace('.npy', ext)
        all_tracks.add((feat_path, audio_dir, mel_dir, ext))
    for i in range(len(unseen_valid_list)):
        _, feat_path, _ = unseen_valid_list[i]
        feat_path = feat_path.replace('.npy', ext)
        all_tracks.add((feat_path, audio_dir, mel_dir, ext))

    all_tracks = list(all_tracks)
    print (len(all_tracks))
    
    with Pool(N_WORKERS) as p:
        p.starmap(parallel_mel, all_tracks)
    

def process_damp_mix():
    import damp_config
    process_damp(damp_config.mix_audio_dir, damp_config.mix_mel_dir, '.wav')

def process_damp_vocal():
    import damp_config
    process_damp(damp_config.vocal_audio_dir, damp_config.vocal_mel_dir, '.m4a')


if __name__ == '__main__' : 

    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=str, required=True, choices=['msd', 'damp_mix', 'damp_vocal'])
    args = parser.parse_args()
    print(args)


    if args.dataset == 'msd' : 
        process_msd_singer()
    elif args.dataset == 'damp_mix':
        process_damp_mix()
    elif args.dataset == 'damp_vocal' : 
        process_damp_vocal()
    else : 
        print("Error: Wrong dataset name. Check argument")
