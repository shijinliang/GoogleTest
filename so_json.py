#!/usr/bin/python3
#-*- coding: utf-8 -*-
# Python 3.8.2

import os
import sys
import optparse
import subprocess
import datetime
import json

file_list = []
out_json = {}

def handle_file_info(file_str):
    global file_list
    list = file_str.split(" ")
    if len(list) == 3:
        obj = {}
        obj['file_id'] = list[1]
        path = list[2]
        obj['file_name'] = os.path.basename(path)
        obj['file_path'] = path
        
        file_list.append(obj)

def get_file_info(file_id):
    global file_list
    for file in file_list:
        if file_id == file['file_id']:
            return file

def get_os_info(str):
    global out_json
    list = str.split(" ")
    if len(list) >= 5:
        out_json['format'] = list[1]
        out_json['arch'] = list[2]
        out_json['uUID'] = list[3]
        out_json['file'] = list[4]
        out_json['builtTime'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print("头部信息")
        print(out_json)

# 开始处理文件
def main_func(lines):
    global out_json
    symbol_list = []
    func_name = ''
    # 记录当前状态， -1未开始匹配，-2遇到public结束，遇到FUNC 记录+1
    func_index = -1

    for line in lines:
        if line.endswith('\n'):
            line = line[:-1]
        if line.startswith('MODULE'):
            # MODULE 
            get_os_info(line)
        elif line.startswith('INFO CODE_ID'):
            code_id = line.replace('INFO CODE_ID ', '')
            print("codeID：", code_id)
        elif line.startswith('FILE'):
            handle_file_info(line)
        elif line.startswith('FUNC'):
            # 记录Func
            func_index += 1
            func_list = line.split(' ')
            if len(func_list) >= 5:
                # 函数名可能存在空格，此处整合数据处理
                func_name = ' '.join(func_list[4:])
            else:
                # 解析出错
                print('解析FUNC出错')
                func_name = ''
        elif line.startswith('PUBLIC'):
            print('遇到PUBLIC 结束程序')
            break
        else:
            # 处理func 偏移量
            if func_index >= 0 and func_name != '':
                ''' 示例：起始地址、size、行号、文件id
                e9498 30 32 136
                '''
                list = line.split(' ')
                if len(list) == 4:
                    startAddr = int(list[0], 16)
                    size = int(list[1], 16)
                    line_num = list[2]
                    file_id = list[3]
                    file_obj = get_file_info(file_id)
                    symbol_result = func_name
                    if file_obj is not None and len(file_obj) > 0 :
                        symbol_result = symbol_result + ' ({0}:{1})\n{2}'.format(file_obj['file_name'], line_num, file_obj['file_path'])
                    
                    bt_obj = {}
                    bt_obj['offset_start'] = startAddr
                    bt_obj['offset_end'] = startAddr + size
                    bt_obj['symbol_result'] = symbol_result
                    symbol_list.append(bt_obj)
    
    out_json["symbolTable"] = symbol_list


# 执行dump_syms命令
def exec_dump_syms(file):
    out_file = file.replace('.so', '.symbol')
    command = 'dump_syms ' + file + ' > ' + out_file
    # command = 'echo $PATH'
    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE, encoding="utf-8")
    if result.stderr != '':
        print('dump_syms 命令执行失败，退出程序')
        print(result.stderr)
        exit()
    else:
        return out_file
    

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option("-i", "--input_file")
    parser.add_option("-o", "--output_file")
    (options, args) = parser.parse_args()
    if not (options.input_file and options.output_file):
        parser.print_help()
        sys.exit(1)
        
    # 对so文件先执行命令解析，得到中间产物
    out_file = exec_dump_syms(options.input_file)
    print('dump_syms执行成功，生成文件: ', out_file)
    # 拿到符号表文件
    lines = open(out_file, 'r').readlines()
    main_func(lines)

    fout = open(options.output_file, 'w')
    fout.write(json.dumps(out_json, indent=2))
    rm_command = 'rm ' + out_file
    subprocess.run(rm_command, shell=True)