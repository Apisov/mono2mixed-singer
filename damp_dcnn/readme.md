## Train and test singer classification model
Uses the DAMP original and mashup dataset 

### To train classification model for monophonic or mixed tracks 
```
# to train with monophonic tracks 
python train.py --model_name blahblah --data_type mono

# to train with mixed tracks 
python train.py --model_name blahblah --data_type mix
```

### Trained model
* Mix
    * `models/mixed_1000.h5`
* Mono
    * `models/mono_1000.h5`


