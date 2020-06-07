from sklearn.metrics import roc_auc_score
import torch
from torchnlp.metrics import get_accuracy
from core.utils.configuration import configmapper

@configmapper.map('metrics','binary_auroc')
def binary_auroc(outputs,labels):
    """Function to compute Area Under ROC Curve Score

    Parameters
    ----------
    outputs: torch.Tensor
        Tensor containing the softmax outputs from the model
    labels: torch.Tensor
        Tensor containing the labels (Not one-hot encoded)

    Returns
    -------
    roc_auc_score : int,
        The roc_auc_score computed between the outputs and the labels

    ## Update tips:
    ## More functionality can be added through the parameters.
    ## Custom AUROC function/class can also be defined.
    """
    outputs_index = outputs[:,1]
    return roc_auc_score(labels.detach().numpy(),outputs_index.detach().numpy())

@configmapper.map('metrics','accuracy')
def accuracy(outputs,labels):
    """Function to compute Accuracy Score

    Parameters
    ----------
    outputs: torch.Tensor
        Tensor containing the softmax outputs from the model
    labels: torch.Tensor
        Tensor containing the labels (Not one-hot encoded)

    Returns
    -------
    accuracy_score : int
        The accuracy_score computed between the outputs and the labels

    ## Update tips:
    ## More functionality can be added through the parameters.
    ## Custom function/class can also be defined.
    """
    outputs_argmax = torch.argmax(outputs,dim=1)
    return get_accuracy(labels,outputs_argmax)[0]