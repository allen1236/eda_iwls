#!/usr/env python3
import http.server
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
    try:
        out = sp.check_output( command, text=True, timeout=timeout )
        return out
    except:
        return ""

# Change this to serve on a different port
PORT = 44444
CORS_ORIGIN = "*"
FNAME_SCORE = "score.csv"


# load score 
data = []
with open(FNAME_SCORE, 'r') as f:
    for line in f.readlines()[1:]:
        toks = line.strip().split(',')
        assert( len(data) == int(toks[0]) )
        data.append( ( int(toks[1]), toks[2], toks[3] ) )
print(data)

def writeCsv( fname ):
    with open(fname, 'w+') as f:
        f.write(f"Benchmark,Best,ID,Date\n")
        for i, d in enumerate(data):
            f.write(f"{i:02d},{d[0]},{d[1]},{d[2]}\n")

class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_POST(self):        
        r, info = self.deal_post_data()
        print(r, info, "by: ", self.client_address)
        f = io.BytesIO()
        msg = f"{info}\n"
        f.write(msg.encode('utf-8'))
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.send_header("Content-Length", str(length))
        self.send_header("Access-Control-Allow-Origin", f"{CORS_ORIGIN}")
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()      

    def deal_post_data(self):
        ctype, pdict = cgi.parse_header(self.headers['Content-Type'])
        pdict['boundary'] = bytes(pdict['boundary'], "utf-8")
        pdict['CONTENT-LENGTH'] = int(self.headers['Content-Length'])
        if ctype == 'multipart/form-data':
            form = cgi.FieldStorage( fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST', 'CONTENT_TYPE':self.headers['Content-Type'], })
            print (type(form))
            fname = "./data/%s"%form["file"].filename
            try:
                if isinstance(form["file"], list):
                    for record in form["file"]:
                        open("./data/%s"%record.filename, "wb").write(record.file.read())
                else:
                    open("./data/%s"%form["file"].filename, "wb").write(form["file"].file.read())
            except IOError:
                    return (False, "Can't create file to write, do you have permission to write?")

            id = form["id"].value
            bm = int(form["bm"].value)
            print(f'fname: {fname} {id} {bm}')

            # check #node and run cec
            cmd = f'&r {fname}; &ps; read_truth -f golden/ex{bm:02d}.truth; cec -n {fname}'
            print(cmd)
            out = ""
            try:
                out = run_command( ['abc', '-c', cmd] )
                print(out)
            except :
                return (True, "Can't open file with ABC")

            best = data[bm][0]
            eq = out.find("Networks are equivalent") != -1
            node = out.find("and =")
            if node == -1:
                return (True, "Can't open file with ABC")
            node = int(removeEsc(out[node+5:].strip()).split()[0])
            if eq:
                if node < best:
                    data[bm] = (node, id, datetime.now().strftime("%Y-%m-%d %H:%M:%S") )
                    writeCsv(FNAME_SCORE)
                    return (True, f"Network is equivalent. The AIG size is {node}. You are now the current best in this case.")
                else:
                    return (True, f"Network is equivalent. The AIG size is {node}. The current best is {best} by {data[bm][1]} at {data[bm][2]}.")
            else:
                return (True, f"Network is not equivalent.")

        return (False, "Unknown Error")

Handler = CustomHTTPRequestHandler


with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print("serving at port", PORT)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.shutdown()