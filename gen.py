#!/usr/env python3
import http.server
import json
import socketserver
import io
import cgi
import subprocess as sp
import re
from datetime import datetime

def removeEsc( text ):
    ansi_escape = re.compile(r'''
        \x1B  # ESC
        (?:   # 7-bit C1 Fe (except CSI)
            [@-Z\\-_]
        |     # or [ for CSI, followed by a control sequence
            \[
            [0-?]*  # Parameter bytes
            [ -/]*  # Intermediate bytes
            [@-~]   # Final byte
        )
    ''', re.VERBOSE)
    result = ansi_escape.sub(' ', text)
    return result

def run_command(command, timeout=None):
    out = sp.check_output( command, text=True, timeout=timeout )
    return out

def getNode(fname):

    cmd = f'&r {fname}; &ps'
    out = removeEsc(run_command( ['abc', '-c', cmd ] ))
    node = out.find("and =")
    node = int(out[node+5:].strip().split()[0])
    return node


def update(fname_tmp, fname_best):

    node_tmp = getNode(fname_tmp)
    node_best = getNode(fname_best)

    cmd = f'&cec {fname_tmp} {fname_best}'
    out = run_command( ['abc', '-c', cmd] )
    eq = out.find("Networks are equivalent") != -1

    if eq and node_tmp < node_best:
        print(f'{fname_best} updated ({node_best}->{node_tmp})')
        run_command( ['cp', '-f', f'{fname_tmp}', f'{fname_best}' ] )

def gen(bm, I, T):

    fname_gol = f"golden/ex{bm:02d}.truth"
    fname_best = f"baseline/{bm:02d}.aig"
    fname_tmp = f"tmp.aig"

    print(f'runnign deepsyn {bm:02d} with I={I} T={T}')
    # cmd = f'read_truth -f {fname_gol}; strash; write_aiger {fname_tmp}; &r {fname_tmp}; &fraig -x; &deepsyn -T 180; &ps; &w {fname_tmp}'
    cmd = f'&r {fname_best}; &fraig -x; &deepsyn -I {I} -T {T}; &ps; &w {fname_tmp}'
    out = removeEsc(run_command( ['abc', '-c', cmd ] ))
    node = out.find("and =")
    node = int(out[node+5:].strip().split()[0])
    
    update(fname_tmp, fname_best)

def gen_csv(fname_csv):

    with open(fname_csv, "w+") as f:

        for i in range(100):

            print(f"gen csv ({i:02d}/99)")
            fname_best = f"baseline/{i:02d}.aig"
            node = getNode(fname_best)

            f.write(f"{i:02d},{node}\n")



if __name__ == "__main__":

    for i in range(43,100):
        gen(i, 10, 20)
        gen(i, 2, 300)
    # gen_csv("best.csv")