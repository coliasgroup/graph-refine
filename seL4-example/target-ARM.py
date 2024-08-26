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

out = open("pre_compliled_funcs.txt", 'w')
for (f, func) in functions.iteritems():
	for s in func.serialise():
		out.write(s + '\n')
out.close()

print 'Pseudo-Compiling.'
pseudo_compile.compile_funcs (functions)

out = open("compliled_funcs.txt", 'w')
for (f, func) in functions.iteritems():
	for s in func.serialise():
		out.write(s + '\n')
out.close()

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

out = open("post_pairings.txt", 'w')
for (f, func) in functions.iteritems():
	for s in func.serialise():
		out.write(s + '\n')
out.close()

import inst_logic
inst_logic.add_inst_specs ()

out = open("post_isns.txt", 'w')
for (f, func) in functions.iteritems():
	for s in func.serialise():
		out.write(s + '\n')
out.close()

f_eqs = open ("pairings.txt", 'w')

print(repr(pairings))
for x in pairings.values():
	assert len(x) == 1
	pairing = x[0]
	f_eqs.write('%s {\n' % pairing.name)
	in_eqs, out_eqs = pairing.eqs
	for (this_label, these_eqs) in [("IN", in_eqs), ("OUT", out_eqs)]:
		for ((l_exp, l_foo), (r_exp, r_foo)) in these_eqs:
			ss = [this_label]
			ss.append(l_foo)
			l_exp.serialise(ss)
			ss.append(r_foo)
			r_exp.serialise(ss)
			f_eqs.write('%s\n' % (' '.join(ss),))
	f_eqs.write ('}\n')
	f_eqs.flush ()

print 'Checking.'
#syntax.check_funs (functions)


