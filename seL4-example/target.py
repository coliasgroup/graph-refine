#
# Copyright 2020, Data61, CSIRO (ABN 41 687 119 230)
#
# SPDX-License-Identifier: BSD-2-Clause
#

from target_objects import target_dir, structs, functions
from target_objects import symbols, sections, rodata, pairings
import target_objects

import syntax
import pseudo_compile
import objdump
import logic
import re

f = open ('%s/kernel.elf.symtab' % target_dir)
objdump.install_syms (f)
f.close ()

f = open ('%s/CFunctions.txt' % target_dir)
syntax.parse_and_install_all (f, 'C')
f.close ()

# These functions never return. This is an assumption about the target:
# the graph language equates reaching a call with returning from it, so
# 'noreturn' cannot be derived, and the decompiler gives every call a
# fall-through continuation at the next address.
#   halt                  spins with interrupts masked
#   idle_thread           spins waiting for an interrupt
#   restore_user_context  leaves the kernel by exception return
#   c_handle_vm_fault     handles the fault and leaves by the same route
# Where the fall-through address is not part of the calling function its
# continuation node is missing, and syntax.check_cfg already patches it
# to an error node; this makes the same patch where the address happens
# to be real code of the same function, which otherwise manufactures a
# spurious cycle (the noreturn tail of c_handle_interrupt at -O2). The
# patch only prunes executions in which one of these functions returns,
# which the target cannot perform, so a refinement proof of a patched
# function is a proof of the unpatched one. Note that it can leave a
# function with no reachable Ret, which makes its refinement obligations
# vacuous (see the TODO in check.leaf_condition_checks).
noreturn_fnames = ['halt', 'idle_thread', 'restore_user_context',
	'c_handle_vm_fault']

f = open ('%s/ASMFunctions.txt' % target_dir)
(astructs, afunctions, aconst_globals) = syntax.parse_and_install_all (f, 'ASM',
	skip_functions = ['fastpath_call', 'fastpath_reply_recv',
		'c_handle_syscall', 'arm_swi_syscall'],
	noreturn_functions = noreturn_fnames)
f.close ()
assert not astructs
assert not aconst_globals

assert logic.aligned_address_sanity (afunctions, symbols, 4)

f = open ('%s/kernel.elf.rodata' % target_dir)
objdump.install_rodata (f, [('Section', '.rodata'), ('Symbol', 'kernel_device_frames'),
	('Symbol', 'avail_p_regs')])
f.close ()

print 'Pseudo-Compiling.'
pseudo_compile.compile_funcs (functions)

print 'Doing stack/inst logic.'

def make_pairings ():
	pairs = [(s, 'Kernel_C.' + s) for s in functions
		if ('Kernel_C.' + s) in functions]
	target_objects.use_hooks.add ('stack_logic')
	import stack_logic
	stack_bounds = '%s/StackBounds.txt' % target_dir
	new_pairings = stack_logic.mk_stack_pairings (pairs, stack_bounds)
	pairings.update (new_pairings)

make_pairings ()

import inst_logic
inst_logic.add_inst_specs ()

print 'Checking.'
syntax.check_funs (functions)


