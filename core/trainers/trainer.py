import os
import torch
from core.utils.mapper import configmapper
from core.utils.configuration import Config
from core.modules.optimizers import *
from core.modules.schedulers import *
from core.modules.losses import *
from core.modules.builder import *
from core.modules.metrics import *
from core.utils.logger import Logger
from torch.utils.data import Dataset,DataLoader
from tqdm import tqdm

import os
from torch.utils.data import Dataset,DataLoader
from tqdm import tqdm

@configmapper.map("trainers","trainer")
class Trainer:
    def __init__(self,config):
        self._config = config
        self.metrics = [configmapper.get_object('metrics',metric) for metric in self._config.main_config.metrics]
        self.train_config = self._config.train
        self.eval_config = self._config.eval
## Train
    def train(self,model,dataset,verbose,tqdm_out=True,eval_dataset=None):

        optim_params = self.train_config.optimizer.params
        if(optim_params):
            optimizer = configmapper.get_object('optimizers',self.train_config.optimizer.type)(model.parameters(),**map_dict_to_obj(optim_params.as_dict()))
        else:
            optimizer = configmapper.get_object('optimizers',self.train_config.optimizer.type)(model.parameters())

        scheduler_params = self.train_config.scheduler.params
        if(scheduler_params):
            scheduler = configmapper.get_object('schedulers',self.train_config.scheduler.type)(optimizer,**map_dict_to_obj(scheduler_params.as_dict()))
        else:
            scheduler = configmapper.get_object('schedulers',self.train_config.scheduler.type)(optimizer)

        criterion_params = self.train_config.criterion.params
        if(criterion_params):
            criterion = configmapper.get_object('losses',self.train_config.criterion.type)(**map_dict_to_obj(criterion_params.as_dict()))
        else:
            criterion = configmapper.get_object('losses',self.train_config.criterion.type)()

        train_loader = DataLoader(dataset,**self.train_config.loader_params.as_dict())
        train_logger = Logger(**self.train_config.log.logger_params.as_dict())
        log_interval = self.train_config.log.log_interval
        eval_interval = self.train_config.eval_interval
        max_steps = self.train_config.max_steps
        log_values = self.train_config.log.values.as_dict()

        step=0
        epoch=0
        break_all=False
        if(tqdm_out):
            pbar = tqdm(total = max_steps)
        print('Starting training...')
        print(max_steps)
        while(step<max_steps):
            epoch+=1
            running_loss = 0
            all_labels = torch.LongTensor()
            all_outputs = torch.Tensor()
            for i,batch in enumerate(train_loader):
                if(step>=max_steps):
                    break_all = True
                    break
                step+=1
                *inputs, labels = [value.to(torch.device(self._config.main_config.device.name)) for value in batch]
                optimizer.zero_grad()
                outputs = model(*inputs)
                loss = criterion(outputs,labels)
                loss.backward()
                all_labels = torch.cat((all_labels,labels),0)
                all_outputs = torch.cat((all_outputs,outputs),0)
                running_loss+=loss.item()
                optimizer.step()
                scheduler.step(epoch + i/len(train_loader))


                if(step%log_interval==log_interval-1):
                    if(log_values['loss']):
                        train_logger.save_params([loss.item()/self.train_config.loader_params.batch_size],['train_loss'],epoch=epoch,batch_size=self.train_config.loader_params.batch_size,batch=i+1)

                    if(log_values['metrics']):
                        train_logger.save_params([metric(outputs,labels) for metric in self.metrics],[metric for metric in self._config.main_config.metrics],combine=True,combine_name='metrics',epoch=epoch,batch_size=self.train_config.loader_params.batch_size,batch=i+1)

                if(eval_dataset is not None and step%eval_interval==eval_interval-1):
                    self.eval(model,eval_dataset,epoch,i,log_values,criterion)
                pbar.update(1)


            loss = running_loss/len(train_loader)
            loss_list = [loss]
            loss_name_list = ['train_loss']

            if(log_values['loss']):
                train_logger.save_params(loss_list,loss_name_list,epoch=epoch,batch_size=self.train_config.loader_params.batch_size,batch=self.train_config.loader_params.batch_size)

            metric_list =[metric(all_outputs,all_labels) for metric in self.metrics]
            metric_name_list= [metric for metric in self._config.main_config.metrics]
            if(log_values['metrics']):
                train_logger.save_params(metric_list,metric_name_list,combine=True,combine_name='metrics',epoch=epoch,batch_size=self.train_config.loader_params.batch_size,batch=self.train_config.loader_params.batch_size)
            print(f'Train, Epoch:{epoch}')
            print(loss_list+metric_list)
            print(loss_name_list+metric_name_list)

            if(break_all):
                break



        if(tqdm_out):
            pbar.close()

## Evaluate
    def eval(self,model,dataset,epoch,i,log_values,criterion):
        eval_logger = Logger(**self.eval_config.log.logger_params.as_dict())
        eval_loader = DataLoader(dataset,**self.eval_config.loader_params.as_dict())
        all_outputs = torch.Tensor()
        all_labels = torch.LongTensor()
        with torch.no_grad():
            val_loss = 0
            for j,batch in enumerate(eval_loader):
                *inputs, labels = [value.to(torch.device(self._config.main_config.device.name)) for value in batch]
                outputs = model(*inputs)
                loss = criterion(outputs,labels)
                val_loss+=loss.item()
                all_labels = torch.cat((all_labels,labels),0)
                all_outputs = torch.cat((all_outputs,outputs),0)
            val_loss = val_loss/len(eval_loader)
            loss_list = [val_loss]
            loss_name_list = ['eval_loss']
            if(log_values['loss']):
                val_logger.save_params(loss_list,loss_name_list,epoch=epoch,batch_size=self.train_config.loader_params.batch_size,batch=i+1)

            metric_list =[metric(all_outputs,all_labels) for metric in self.metrics]
            metric_name_list= [metric for metric in self._config.main_config.metrics]
            if(log_values['metrics']):
                val_logger.save_params(metric_list,metric_name_list,combine=True,combine_name='metrics',epoch=epoch,batch_size=self.eval_config.loader_params.batch_size,batch=i+1)
            print('Evaluation:')
            print(loss_list+metric_list)
            print(loss_name_list+metric_name_list)