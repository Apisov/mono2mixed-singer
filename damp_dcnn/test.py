import os
import sys
import numpy as np
from random import shuffle
import tensorflow as tf 
import tensorflow.keras as keras
from tensorflow.keras import backend as K
from tensorflow.keras import metrics
from tensorflow.keras.models import load_model, Model
from sklearn.metrics.pairwise import cosine_similarity
import argparse
# print (K.tensorflow_backend._get_available_gpus())

import model
import dataloader 
sys.path.append('../')
import damp_config as config

os.environ["CUDA_VISIBLE_DEVICES"] = "3"


parser = argparse.ArgumentParser()
parser.add_argument('--model_path', type=str, required=True)
parser.add_argument('--data_type', type=str, choices=['mix', 'mono'])
args = parser.parse_args()

if args.data_type == 'mono': 
    feat_mean = config.vocal_total_mean
    feat_std = config.vocal_total_std 
    mel_path = config.vocal_mel_dir
else : 
    feat_mean = config.mix_total_mean
    feat_std = config.mix_total_std
    mel_path = config.mix_mel_dir



def build_singer_model(model, train_list, feat_mean, feat_std, mel_path, num_singers, forBuildingModel):
    '''
    Args: 
    Return : 

    '''
    layer_dict = dict([(layer.name, layer) for layer in model.layers[1:]])
    get_last_layer_outputs = K.function([model.layers[0].input, K.learning_phase()], [layer_dict['global_average_pooling1d_1'].output])

    artist_to_track_model = dict.fromkeys(range(0,300), None)
    for i in range(len(train_list)):
        artist_id, feat_path, start_frame = train_list[i]

        if artist_to_track_model[artist_id] == None:
            artist_to_track_model[artist_id] = {}

        if args.data_type == 'mono': 
            feat = np.load(os.path.join(mel_path, feat_path))
            tmp_feat = feat[:, start_frame:start_frame + config.input_frame_len]
        else : 
            feat = np.load(os.path.join(mel_path, feat_path.replace('.npy', '_' + str(start_frame) + '.npy')))
            tmp_feat = feat[:, : config.input_frame_len]

        tmp_feat = tmp_feat.T
        tmp_feat -= feat_mean
        tmp_feat /= feat_std
        tmp_feat = np.expand_dims(tmp_feat, 0)
        pred = get_last_layer_outputs([tmp_feat,  0])[0]
        pred = pred[0]

        try:
            
            artist_to_track_model[artist_id][feat_path].append(pred)
        except:
            artist_to_track_model[artist_id][feat_path] = []
            artist_to_track_model[artist_id][feat_path].append(pred)
    
    if forBuildingModel:
        embs = [] 
        artist_track_answer = [] 
        for k,track_dict in artist_to_track_model.items():
            artist_all_feat= []
            count_tracks = 0 
            for tid,v in track_dict.items():

                artist_all_feat.extend(v)
                for _ in range(len(v)):
                    artist_track_answer.append(k)
                count_tracks +=1 

            artist_all_feat = np.array(artist_all_feat)
            mean = np.mean(artist_all_feat, axis=0)
            embs.append(mean)
            
            track_answer = [] 
        
        embs = np.array(embs)

        return embs, artist_track_answer 
    else :
        embs = []
        track_answer = [] 
        for k,track_dict in artist_to_track_model.items():
            for tid,v in track_dict.items():
                v = np.array(v)
                mean = np.mean(v, axis=0)
                embs.append(mean)
                track_answer.append(k)
        embs = np.array(embs)
        track_answer = np.array(track_answer)
        return embs, track_answer 

        


def test():
    global mel_path, feat_mean, feat_std
    
    # load data 
    artist_list = np.load('../data/unseen_artist_300_2.npy')
    train_list, _  = dataloader.load_data_segment('../data/unseen_model_artist_track_300_2.pkl',artist_list)
    test_list, _ = dataloader.load_data_segment('../data/unseen_eval_artist_track_300_2.pkl', artist_list)
    print ('train, test', len(train_list), len(test_list))

    # load model 
    mymodel = load_model(args.model_path)
    print (mymodel.summary())

    # inference on test data 
    artist_embeddings, artist_track_answer = build_singer_model(mymodel, train_list, feat_mean, feat_std, mel_path, 300, forBuildingModel=True)
    track_embeddings, track_answer = build_singer_model(mymodel, test_list, feat_mean, feat_std, mel_path, 300, forBuildingModel=False)
    
    # compute cosine similarity 
    cos_sim = cosine_similarity(track_embeddings, artist_embeddings)
    # top-1 acc
    pred_score = np.argmax(np.array(cos_sim), axis=1)
    sim_correct = sum(pred_score == track_answer) # correct:1, incorrect:0
    sim_acc = sim_correct / len(track_embeddings)
    print ('Similarity Correct: %d/%d, Acc:%.4f'%(sim_correct , len(track_embeddings), sim_acc))
    
    # top-k accuracy 
    k=5
    pred_scores = np.argsort(-np.array(cos_sim), axis=1)
    top_k_correct= 0
    for i in range(len(pred_scores)):
        if track_answer[i] in pred_scores[i][:k]:
            top_k_correct += 1

    print ("top k: %d/%d, acc:%.4f"%(top_k_correct, len(track_embeddings), top_k_correct/len(track_embeddings)))



if __name__ == '__main__':
    test()

