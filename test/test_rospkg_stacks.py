# Software License Agreement (BSD License)
#
# Copyright (c) 2011, Willow Garage, Inc.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following
#    disclaimer in the documentation and/or other materials provided
#    with the distribution.
#  * Neither the name of Willow Garage, Inc. nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import os
import sys
import time
  
import subprocess

def rosstackexec(args):
    rosstack_bin = os.path.join(os.environ['ROS_ROOT'], 'bin', 'rosstack')
    val = (subprocess.Popen([rosstack_bin] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()[0] or '').strip()
    if val.startswith('rosstack:'): #rosstack error message
        raise Exception(val)
    return val

# for comparing against 'ground truth'
def rosstack_list():
    return [s.split()[0] for s in rosstackexec(['list']).split('\n')]
def rosstack_find(package):
    return rosstackexec(['find', package]).strip()
def rosstack_depends(package):
    return unicode(rosstackexec(['depends', package])).split()
def rosstack_depends1(package):
    return unicode(rosstackexec(['depends1', package])).split()

def delete_cache():
    from rospkg import get_ros_home
    p = os.path.join(get_ros_home(), 'rosstack_cache')
    if os.path.exists(p):
        os.remove(p)
    
def test_RosStack_list():
    from rospkg import RosStack
    r = RosStack()

    l = rosstack_list()
    retval = r.list()
    assert set(l) == set(retval), "%s vs %s"%(l, retval)
    
    # test twice for caching
    retval = r.list()
    assert set(l) == set(retval), "%s vs %s"%(l, retval)

    # make sure stress test works with rospack_cache invalidated
    delete_cache()
    r = RosStack()
    retval = r.list()
    assert set(l) == set(retval), "%s vs %s"%(l, retval)

def get_stack_test_path():
    return os.path.abspath(os.path.join(sys.path[0], 'stack_tests'))

def test_RosStack_get_path():
    from rospkg import RosStack, ResourceNotFound

    path = get_stack_test_path()
    bar_path = os.path.join(path, 's1', 'bar')
    baz_path = os.path.join(path, 's2', 'baz')
    
    # point ROS_ROOT at top, should spider entire tree
    print("ROS_ROOT: %s"%(path))
    print("ROS_PACKAGE_PATH: ")
    r = RosStack(ros_root=path, ros_package_path='')
    assert bar_path == r.get_path('bar'), "%s vs. %s"%(bar_path, r.get_path('bar'))
    assert baz_path == r.get_path('baz'), "%s vs. %s"%(baz_path, r.get_path('baz'))
    try:
        r.get_path('fake')
        assert False
    except ResourceNotFound:
        pass
    
    # divide tree in half to test precedence
    print("ROS_ROOT: %s"%(os.path.join(path, 'p1')))
    print("ROS_PACKAGE_PATH: %s"%(os.path.join(path, 'p2')))
    foo_path = os.path.join(path, 's1', 'foo')
    r = RosStack(ros_root=os.path.join(path, 's1'), ros_package_path=os.path.join(path, 's2'))
    assert foo_path == r.get_path('foo'), "%s vs. %s"%(foo_path, r.get_path('foo'))
    assert bar_path == r.get_path('bar')
    assert baz_path == r.get_path('baz')

    # divide tree in half again and test precedence of ROS_PACKAGE_PATH (foo should switch)
    print("ROS_ROOT: %s"%(os.path.join(path, 'p1')))
    print("ROS_PACKAGE_PATH: %s"%(os.path.join(path, 'p2')))
    foo_path = os.path.join(path, 's2', 'foo')
    r = RosStack(ros_root=os.path.join(path, 'notapath'), ros_package_path="%s%s%s"%(os.path.join(path, 's2'), os.pathsep, os.path.join(path, 's1')))
    assert foo_path == r.get_path('foo'), "%s vs. %s"%(foo_path, r.get_path('foo'))

    # stresstest against rospack
    r = RosStack()
    listval = rosstack_list()
    for p in listval:
        retval = r.get_path(p)
        rospackval = rosstack_find(p)
        assert retval == rospackval, "[%s]: %s vs. %s"%(p, retval, rospackval)

    # stresstest with cache invalidated
    delete_cache()
    r = RosStack() 
    for p in listval:
        retval = r.get_path(p)
        rospackval = rosstack_find(p)
        assert retval == rospackval, "[%s]: %s vs. %s"%(p, retval, rospackval)

def test_RosStack_get_depends():
    from rospkg import RosStack, ResourceNotFound
    path = get_stack_test_path()
    s1 = os.path.join(path, 's1')
    s3 = os.path.join(path, 's3')
    r = RosStack(ros_root=s1, ros_package_path=s3)

    # TODO: need one more step
    assert set(r.get_depends('baz')) == set(['foo', 'bar'])
    assert r.get_depends('bar') == ['foo']
    assert r.get_depends('foo') == []

    # stress test: test default environment against rosstack
    r = RosStack()
    
    for p in rosstack_list():
        retval = set(r.get_depends(p))
        rospackval = set(rosstack_depends(p))
        assert retval == rospackval, "[%s]: %s vs. %s"%(p, retval, rospackval)
    
def test_RosStack_get_direct_depends():
    from rospkg import RosStack, ResourceNotFound
    path = get_stack_test_path()
    s1 = os.path.join(path, 's1')
    s3 = os.path.join(path, 's3')
    r = RosStack(ros_root=s1, ros_package_path=s3)

    assert set(r.get_direct_depends('baz')) == set(['bar', 'foo'])
    assert r.get_direct_depends('bar') == ['foo']
    assert r.get_direct_depends('foo') == []

    # stress test: test default environment against rospack
    r = RosStack()
    for p in rosstack_list():
        retval = set(r.get_direct_depends(p))
        rospackval = set(rosstack_depends1(p))
        assert retval == rospackval, "[%s]: %s vs. %s"%(p, retval, rospackval)

def test_expand_to_packages():
    from rospkg import expand_to_packages, RosPack, RosStack
    path = os.path.join(get_stack_test_path(), 's1')
    rospack = RosPack(ros_root=path, ros_package_path='')
    rosstack = RosStack(ros_root=path, ros_package_path='')

    try:
        expand_to_packages('foo', rospack, rosstack)
        assert False, "should have raised ValueError"
    except ValueError:
        pass
    
    valid, invalid = expand_to_packages(['foo'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2'])
    assert not invalid
    
    valid, invalid = expand_to_packages(['foo_pkg'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg'])
    assert not invalid
    
    valid, invalid = expand_to_packages(['foo', 'foo_pkg'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2'])
    assert not invalid
    
    valid, invalid = expand_to_packages(['foo', 'bar'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2', 'bar_pkg'])
    assert not invalid
                                
    valid, invalid = expand_to_packages(['foo', 'bar_pkg'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2', 'bar_pkg'])
    assert not invalid
                                
    valid, invalid = expand_to_packages(['foo', 'bar_pkg', 'bar'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2', 'bar_pkg'])
    assert not invalid

    valid, invalid = expand_to_packages(['foo', 'fake1', 'bar_pkg', 'bar', 'fake2'], rospack, rosstack)
    assert set(valid) == set(['foo_pkg', 'foo_pkg_2', 'bar_pkg'])
    assert set(invalid) == set(['fake1', 'fake2'])
                                
def test_get_stack_version():
    from rospkg import get_stack_version_by_dir, RosStack
    path = os.path.join(get_stack_test_path(), 's1')
    r = RosStack(ros_root=path, ros_package_path='')

    # test by dir option directly
    foo_dir = r.get_path('foo')
    assert get_stack_version_by_dir(foo_dir) == '1.6.0-manifest'
    bar_dir = r.get_path('bar')
    assert get_stack_version_by_dir(bar_dir) == '1.5.0-cmake'

    # test via rosstack
    assert r.get_stack_version('foo') == '1.6.0-manifest'    
    assert r.get_stack_version('bar') == '1.5.0-cmake'    

    path = os.path.join(get_stack_test_path(), 's2')
    r = RosStack(ros_root=path, ros_package_path='')
    foo_dir = r.get_path('foo')
    assert get_stack_version_by_dir(foo_dir) == None, get_stack_version_by_dir(foo_dir)
    baz_dir = r.get_path('baz')
    assert get_stack_version_by_dir(baz_dir) == None

def test_get_cmake_version():
    from rospkg.rospack import _get_cmake_version
    
    assert '1.6.0' == _get_cmake_version("rosbuild_make_distribution(1.6.0)")
    try:
        _get_cmake_version("rosbuild_make_distribution")
        assert False, "should have raised ValueError"
    except ValueError:
        pass