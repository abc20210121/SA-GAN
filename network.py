import os, pickle
import numpy as np
import torch
import torch.nn as nn


def weights_init(mod):
    """
    Custom weights initialization called on netG, netD and netE
    :param m:
    :return:
    """
    classname = mod.__class__.__name__
    if classname.find('Conv') != -1:
        # mod.weight.data.normal_(0.0, 0.02)
        nn.init.xavier_normal_(mod.weight.data)
        # nn.init.kaiming_uniform_(mod.weight.data)

    elif classname.find('BatchNorm') != -1:
        mod.weight.data.normal_(1.0, 0.02)
        mod.bias.data.fill_(0)
    elif classname.find('Linear') != -1:
        torch.nn.init.xavier_uniform_(mod.weight)
        mod.bias.data.fill_(0.01)


class Encoder(nn.Module):
    def __init__(self, ngpu, opt, out_z):
        super(Encoder, self).__init__()
        self.ngpu = ngpu
        self.softplus = nn.Softplus()
        self.main = nn.Sequential(
            # input is dim x 128
            nn.Conv1d(opt.dim, opt.ndf, 4, 2, 1),
            nn.BatchNorm1d(opt.ndf),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf) x 64

            nn.Conv1d(opt.ndf, opt.ndf * 2, 4, 2, 1),
            nn.BatchNorm1d(opt.ndf * 2),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*2) x 32

            nn.Conv1d(opt.ndf * 2, opt.ndf * 4, 4, 2, 1),
            nn.BatchNorm1d(opt.ndf * 4),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*4) x 16

            nn.Conv1d(opt.ndf * 4, opt.ndf * 8, 4, 2, 1),
            nn.BatchNorm1d(opt.ndf * 8),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*8) x 8

            nn.Conv1d(opt.ndf * 8, opt.ndf * 16, 4, 2, 1),
            nn.BatchNorm1d(opt.ndf * 16),
            nn.LeakyReLU(0.2, inplace=True),
            # state size. (ndf*16) x 4
        )

        self.mu = nn.Conv1d(opt.ndf*16, out_z, 4, 1, 0)
        self.log_var = nn.Conv1d(opt.ndf*16, out_z, 4, 1, 0)

    def forward(self, input):

        output = self.main(input)
        mu = self.mu(output)
        log_var = self.softplus(self.log_var(output)) + 1e-4

        return mu, log_var


##


class Decoder(nn.Module):
    def __init__(self, ngpu, opt):
        super(Decoder, self).__init__()
        self.ngpu = ngpu
        self.main = nn.Sequential(
            # input is Z, going into a convolution
            nn.ConvTranspose1d(opt.nz, opt.ngf * 16, 4, 1, 0),
            nn.BatchNorm1d(opt.ngf * 16),
            nn.ReLU(True),
            # state size. (ngf*16) x 4

            nn.ConvTranspose1d(opt.ngf * 16, opt.ngf * 8, 4, 2, 1),
            nn.BatchNorm1d(opt.ngf * 8),
            nn.ReLU(True),
            # state size. (ngf*8) x 8

            nn.ConvTranspose1d(opt.ngf * 8, opt.ngf * 4, 4, 2, 1),
            nn.BatchNorm1d(opt.ngf * 4),
            nn.ReLU(True),
            # state size. (ngf*4) x 16

            nn.ConvTranspose1d(opt.ngf * 4, opt.ngf * 2, 4, 2, 1),
            nn.BatchNorm1d(opt.ngf * 2),
            nn.ReLU(True),
            # state size. (ngf*2) x 32

            nn.ConvTranspose1d(opt.ngf * 2, opt.ngf, 4, 2, 1),
            nn.BatchNorm1d(opt.ngf),
            nn.ReLU(True),
            # state size. (ngf) x 64

            nn.ConvTranspose1d(opt.ngf, opt.dim, 4, 2, 1),
            nn.Sigmoid()
            # state size. (dim) x 128

        )

    def forward(self, input):

        output = self.main(input)
        return output


class SA_MODEL(object):
    def __init__(self, opt):
        self.G = None
        self.D_rec = None
        self.D_lat = None

        self.opt = opt
        self.niter = opt.niter
        self.dataset = opt.dataset
        self.model = opt.model
        self.outf = opt.outf

    def train(self):
        raise NotImplementedError



    def save(self, train_hist):
        save_dir = os.path.join(self.outf, self.model, self.dataset)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        with open(os.path.join(save_dir, self.model + '_history.pkl'), 'wb') as f:
            pickle.dump(train_hist, f)

    def save_weight_GD(self):
        save_dir = os.path.join(self.outf, self.model, self.dataset)

        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        torch.save(self.G.state_dict(),
                   os.path.join(save_dir,
                                self.opt.model + "_" + str(self.opt.filename) + '_' + str(self.opt.update_method)
                                + '_' + str(self.opt.delta)
                                + '_' + str(self.opt.ratio)
                                + '_' + str(self.opt.sample_method) + '_G.pkl'))
        # torch.save(self.D_rec.state_dict(),
        #            os.path.join(save_dir, self.model + "_folder_" + str(self.opt.folder) + '_D_rec.pkl'))
        # torch.save(self.D_lat.state_dict(),
        #            os.path.join(save_dir, self.model + "_folder_" + str(self.opt.folder) + '_D_lat.pkl'))

    def load(self):
        save_dir = os.path.join(self.outf, self.model, self.dataset)

        self.G.load_state_dict(
            torch.load(os.path.join(save_dir,
                                self.opt.model + "_" + str(self.opt.filename) + '_' + str(self.opt.update_method)
                                + '_' + str(self.opt.delta)
                                + '_' + str(self.opt.ratio)
                                + '_' + str(self.opt.sample_method) + '_G.pkl')))
        # self.D_rec.load_state_dict(
        #     torch.load(os.path.join(save_dir, self.model + "_folder_" + str(self.opt.folder) + '_D_rec.pkl')))
        # self.D_lat.load_state_dict(
        #     torch.load(os.path.join(save_dir, self.model + "_folder_" + str(self.opt.folder) + '_D_lat.pkl')))


