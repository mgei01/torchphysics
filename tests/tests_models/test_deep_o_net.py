import torch
import pytest

from torchphysics.models.deeponet.subnets import (TrunkNet, FCTrunkNet, 
                                                  BranchNet, FCBranchNet)
from torchphysics.models.deeponet.deeponet import DeepONet
from torchphysics.models.model import Sequential, NormalizationLayer
from torchphysics.problem.spaces import Points, R1, R2, FunctionSpace
from torchphysics.problem.domains import Interval, CustomFunctionSet
from torchphysics.problem.samplers.grid_samplers import GridSampler

"""
Tests for trunk net:
"""

def test_create_trunk_net():
    net = TrunkNet(input_space=R2('x'), output_space=R1('u'), output_neurons=20)
    assert net.input_space == R2('x')
    assert net.output_space == R1('u')
    assert net.output_neurons == 20


def test_create_fc_trunk_net():
    net = FCTrunkNet(input_space=R2('x'), output_space=R1('u'), output_neurons=20)
    assert net.input_space == R2('x')
    assert net.output_space == R1('u')
    assert net.output_neurons == 20


def test_forward_fc_trunk_net():
    net =  FCTrunkNet(input_space=R2('x'), output_space=R1('u'), output_neurons=20)
    test_data = Points(torch.tensor([[2, 3.0], [0, 1]]), R2('x'))
    out = net(test_data)
    assert out.size() == torch.Size([2, 20])

"""
Tests for branch net:
"""
def helper_fn_set():
    def f(k, t):
        return k*t
    inter = Interval(R1('t'), 0, 1)
    params = Interval(R1('k'), 0, 1)
    fn_space = FunctionSpace(inter, R1('e'))
    fn_set =  CustomFunctionSet(fn_space, GridSampler(params, 20), f)
    return fn_space, fn_set


def test_create_branch_net():
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 10).make_static()
    net = BranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                    discretization_sampler=sampler)
    assert net.discretization_sampler == sampler
    assert net.output_space == R1('u')
    assert net.output_neurons == 20
    assert net.input_dim == 10
    assert net.input_space == fn_space


def test_discretization_of_function_set():
    fn_space, fn_set = helper_fn_set()
    fn_set.sample_params()
    sampler = GridSampler(fn_space.input_domain, 10).make_static()
    net = BranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                    discretization_sampler=sampler)
    fn_batch = net._discretize_function_set(fn_set)
    assert fn_batch.shape == (20, 10)


def test_create_fc_branch_net():
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    net = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=22, 
                      discretization_sampler=sampler)
    assert net.discretization_sampler == sampler
    assert net.output_space == R1('u')
    assert net.output_neurons == 22
    assert net.input_dim == 15
    assert net.input_space == fn_space


def test_fix_branch_net_with_function():
    def f(t):
        return 20*t
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    net = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=22, 
                      discretization_sampler=sampler)
    net.fix_input(f)
    assert net.current_out.shape == (1, 22)


def test_fix_branch_net_with_function_2():
    def f(t):
        return 20*t.T + 4.0
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    net = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=22, 
                      discretization_sampler=sampler)
    net.fix_input(f)
    assert net.current_out.shape == (1, 22)


def test_fix_branch_net_with_function_set():
    fn_space, fn_set = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    net = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=22, 
                      discretization_sampler=sampler)
    net.fix_input(fn_set)
    assert net.current_out.shape == (20, 22)


def test_fix_branch_wrong_input():
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    net = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=22, 
                      discretization_sampler=sampler)
    with pytest.raises(NotImplementedError):
        net.fix_input(34)

"""
Tests for DeepONet:
"""
def test_create_deeponet():
    trunk = TrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(trunk, branch)
    assert net.trunk == trunk
    assert net.branch == branch
    assert net.input_space == R1('t')
    assert net.output_space == R1('u')


def test_create_deeponet_with_seq_trunk():
    trunk = TrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    seq_trunk = Sequential(NormalizationLayer(Interval(R1('t'), 0, 1)), trunk)
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(seq_trunk, branch)
    assert net.trunk == seq_trunk
    assert net.branch == branch
    assert net.input_space == R1('t')
    assert net.output_space == R1('u')
    

def test_create_deeponet_fix_branch():
    def f(t):
        return 20*t
    trunk = TrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(trunk, branch)
    net.fix_branch_input(f)
    assert branch.current_out.shape == (1, 20)


def test_deeponet_forward():
    def f(t):
        return 20*t
    trunk = FCTrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(trunk, branch)
    in_sampler = GridSampler(Interval(R1('t'), 0, 1), 50)
    out = net(in_sampler.sample_points(), f)
    assert 'u' in out.space
    assert out.as_tensor.shape == (1, 50, 1)


def test_deeponet_forward_with_fixed_branch():
    def f(t):
        return torch.sin(t)
    trunk = FCTrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    fn_space, _ = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(trunk, branch)
    in_sampler = GridSampler(Interval(R1('t'), 0, 1), 50)
    net.fix_branch_input(f)
    out = net(in_sampler.sample_points())
    assert 'u' in out.space
    assert out.as_tensor.shape == (1, 50, 1)


def test_deeponet_forward_branch_intern():
    trunk = FCTrunkNet(input_space=R1('t'), output_space=R1('u'), output_neurons=20)
    fn_space, fn_set = helper_fn_set()
    sampler = GridSampler(fn_space.input_domain, 15).make_static()
    branch = FCBranchNet(fn_space, output_space=R1('u'), output_neurons=20, 
                         discretization_sampler=sampler)
    net = DeepONet(trunk, branch)
    net._forward_branch(fn_set, iteration_num=0)
    net._forward_branch(fn_set, iteration_num=0)