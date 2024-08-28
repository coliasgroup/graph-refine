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

syntax.set_arch('armv7')
f = open ('%s/kernel.elf.symtab' % target_dir)
objdump.install_syms (f)
f.close ()

f = open ('%s/CFunctions.txt' % target_dir)
syntax.parse_and_install_all (f, 'C')
f.close ()

f = open ('%s/ASMFunctions.txt' % target_dir)
(astructs, afunctions, aconst_globals) = syntax.parse_and_install_all (f, 'ASM',skip_functions= ['fastpath_call', 'fastpath_reply_recv','c_handle_syscall','arm_swi_syscall'])
f.close ()
assert not astructs
assert not aconst_globals

#assert logic.aligned_address_sanity (afunctions, symbols, 4)

f = open ('%s/kernel.elf.rodata' % target_dir)
objdump.install_rodata (f,
        [
            ('Section', '.rodata'),
            #('Symbol', 'kernel_devices'),
	    ('Symbol', 'avail_p_regs'),
        ]
)
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

def print_pairings():
	f = open('pairings.txt', 'w')

	for x in pairings.values():
		assert len(x) == 1
		pairing = x[0]
		f.write('%s {\n' % pairing.name)
		in_eqs, out_eqs = pairing.eqs
		for (tag, eqs) in [('IN', in_eqs), ('OUT', out_eqs)]:
			for ((l_expr, l_quadrant), (r_expr, r_quadrant)) in eqs:
				ss = [this_label]
				ss.append(l_quadrant)
				l_expr.serialise(ss)
				ss.append(r_quadrant)
				r_expr.serialise(ss)
				f.write('%s\n' % (' '.join(ss),))
		f.write ('}\n')
		f.flush ()

print_pairings()

print 'Checking.'
#syntax.check_funs (functions)


