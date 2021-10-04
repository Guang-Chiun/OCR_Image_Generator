# -*- coding: utf-8 -*-
"""
 -*- coding: utf-8 -*-
 @author: zcswdt
 @email: jhsignal@126.com
 @file: Color_OCR_image_generator.py
 @time: 2020/06/24
"""
import cv2
import numpy as np
import pickle
import random
from PIL import Image,ImageDraw,ImageFont,ImageOps
import os
import shutil
import glob
import pathlib
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import time

import hashlib
from fontTools.ttLib import TTCollection, TTFont
import argparse
import random

from tools.config import load_config
from noiser import Noiser
from tools.utils import apply


from data_aug import apply_blur_on_output
from data_aug import apply_prydown
from data_aug import apply_lr_motion
from data_aug import apply_up_motion


class FontColor(object):
    def __init__(self, col_file):
        with open(col_file, 'rb') as f:
            u = pickle._Unpickler(f)
            u.encoding = 'latin1'
            self.colorsRGB = u.load()
        self.ncol = self.colorsRGB.shape[0]

        # convert color-means from RGB to LAB for better nearest neighbour
        # computations:
        self.colorsRGB = np.r_[self.colorsRGB[:, 0:3], self.colorsRGB[:, 6:9]].astype('uint8')
        self.colorsLAB = np.squeeze(cv2.cvtColor(self.colorsRGB[None, :, :], cv2.COLOR_RGB2Lab))


def Lab2RGB(c):
    if type(c) == list:
        return cv2.cvtColor(np.array([c], dtype=np.uint8)[None,:],cv2.COLOR_Lab2RGB)
    else:
        return cv2.cvtColor(c[None, :, :],cv2.COLOR_Lab2RGB)


def RGB2Lab(rgb):
    import numpy as np
    if type(rgb) == list:
        return(cv2.cvtColor(np.asarray([rgb],dtype=np.uint8)[None,:],cv2.COLOR_RGB2Lab))
    else:
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2Lab)

def GetFilterList(oriFileList, fileTypeList):
    FilterFiles = []
    for getfile in oriFileList:
        for filetype in fileTypeList:
            if getfile.endswith(filetype):
                FilterFiles.append(getfile)
                break
    return FilterFiles        

# 這裡讀錯了(讀到Readme.md)(可能需要寫個過濾機制)
def get_char_lines(txt_root_path):    
    txt_files = os.listdir(txt_root_path)
    FilterFiles = GetFilterList(txt_files, [".txt"])   #這裡最好加入檔案過濾機制，只能讀txt，有時會讀到 ipydb，造成不能跑
    char_lines = []
    for txt in FilterFiles:
        f = open(os.path.join(txt_root_path,txt),mode='r', encoding='utf-8')
        lines = f.readlines()  #這裡掛了
        f.close()
        for line in lines:
            char_lines.append(line.strip().replace('\xef\xbb\xbf', '').replace('\ufeff', ''))
    return char_lines

# 获取chars
def get_chars(char_lines):
    while True:
        char_line = random.choice(char_lines)
        if len(char_line)>0:
            break
    line_len = len(char_line)         
    char_len = random.randint(1,20)  #  4
    if line_len<=char_len:
        return char_line
    char_start = random.randint(0,line_len-char_len)
    chars = char_line[char_start:(char_start+char_len)]
    return chars


# 选择字体
def chose_font(fonts,font_sizes):
    f_size = random.choice(font_sizes)  # 不满就取最大字号吧
    font = random.choice(fonts[f_size])
    return font


# 分析图片，获取最适宜的字体颜色
def get_bestcolor(color_lib, crop_lab):
    if crop_lab.size > 4800:
        crop_lab = cv2.resize(crop_lab,(100,16))  #将图像转成100*16大小的图片
    labs = np.reshape(np.asarray(crop_lab), (-1, 3))         #len(labs)长度为160   
    clf = KMeans(n_clusters=8)
    clf.fit(labs)
    
    #clf.labels_是每个聚类中心的数据（假设有八个类，则每个数据标签属于每个类的数据格式就是从0-8），clf.cluster_centers_是每个聚类中心   
    total = [0] * 8
   
    for i in clf.labels_:
        total[i] = total[i] + 1            #计算每个类中总共有多少个数据
 
    clus_result = [[i, j] for i, j in zip(clf.cluster_centers_, total)]  #聚类中心，是一个长度为8的数组
    clus_result.sort(key=lambda x: x[1], reverse=True)    #八个类似这样的数组，第一个数组表示类中心，第二个数字表示属于该类中心的一共有多少数据[[array([242.55732946, 128.1509434 , 122.29608128]), 689], [array([245.03461538, 128.59230769, 125.88846154]), 260],，，，]
  
    color_sample = random.sample(range(color_lib.colorsLAB.shape[0]), 500)   # 范围是（0,9882），随机从这些数字里面选取500个

    
    def caculate_distance(color_lab, clus_result):
        weight = [1, 0.8, 0.6, 0.4, 0.2, 0.1, 0.05, 0.01]
        d = 0
        for c, w in zip(clus_result, weight):

            #计算八个聚类中心和当前所选取颜色距离的标准差之和，每个随机选取的颜色当前聚类中心的差值
            d = d + np.linalg.norm(c[0] - color_lab)           
        return d
 
    color_dis = list(map(lambda x: [caculate_distance(color_lib.colorsLAB[x], clus_result), x], color_sample))   #将color_sample中的每个参数当成x传入函数内,color_lib.colorsLAB[x]是一个元组(r,g,b)也就是字体库里面的颜色
    #color_dis 是一个长度为500的列表[[x,y],[],,,,,]，其中[x,y]其中x表示背景色和当前颜色的距离，y表示该颜色的色号  
    color_dis.sort(key=lambda x: x[0], reverse=True)
    color_num = color_dis[0:200]
    color_l = random.choice(color_num)[1]
    #print('color_dis',color_l)
    #color_num=random.choice(color_dis[0:300])
    #print('color_dis[0][1]',color_dis[0][1])
    return tuple(color_lib.colorsRGB[color_l])
    #return tuple(color_lib.colorsRGB[color_dis[0][1]])
    
def word_in_font(word,unsupport_chars,font_path):
    #print('1',word)
    #sprint('2',unsupport_chars)
    for c in word:
        #print('c',c)
        # 這裡如果print有問題的字元可能會掛
        if c in unsupport_chars:
            print('Retry pick_font(), \'%s\' contains chars \'%s\' not supported by font %s' % (word, c, font_path))  
            return True
        else:
            continue

# 获得水平文本图片 (目前先用這個就好)
def get_horizontal_text_picture(image_file,color_lib,char_lines,fonts_list,font_unsupport_chars,cf,index,save_file_number):
    global YOLOMode
    global WordDictionary  #YOLO Label File 要使用的
    retry = 0
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    w, h = img.size

    while True:              
        width = 0
        height = 0
        chars_size = []
        y_offset = 10 ** 5    
        
        #随机获得不定长的文字
        #chars = get_chars(char_lines)
        #改成按順序取Generate要產的字
        chars = char_lines[index]

        #随机选择一种字体
        font_path = random.choice(fonts_list)
        font_size = random.randint(cf.font_min_size, cf.font_max_size)
        
        #获得字体，及其大小
        font = ImageFont.truetype(font_path, font_size) 
        #不支持的字体文字，按照字体路径在该字典里索引即可        
        unsupport_chars = font_unsupport_chars[font_path]
        numsofchar = len(chars)   
                                  
        for c in chars:
            size = font.getsize(c)
            chars_size.append(size)
            width += size[0]
            
            # set max char height as word height
            if size[1] > height:
                height = size[1]

            # Min chars y offset as word y offset
            # Assume only y offset
            
            c_offset = font.getoffset(c)
            if c_offset[1] < y_offset:
                y_offset = c_offset[1]    
                
        char_space_width = int(height * np.random.uniform(-0.1, 0.3))

        width += (char_space_width * (len(chars) - 1))            
        
        f_w, f_h = width, height #這個跟輸入的背景圖大小有關
        
        if f_w < w:
            # 完美分割时应该取的
            x1 = random.randint(0, w - f_w)
            y1 = random.randint(0, h - f_h)
            x2 = x1 + f_w
            y2 = y1 + f_h
            
            #加一点偏移
            if cf.random_offset:
                print('cf.random_offset',cf.random_offset)
                # 随机加一点偏移，且随机偏移的概率占30%                
                rd = random.random()
                if rd < 0.3:  # 设定偏移的概率
                    crop_y1 = y1 - random.random() / 5 * f_h
                    crop_x1 = x1 - random.random() / 2 * f_h
                    crop_y2 = y2 + random.random() / 5 * f_h
                    crop_x2 = x2 + random.random() / 2 * f_h
                    crop_y1 = int(max(0, crop_y1))
                    crop_x1 = int(max(0, crop_x1))
                    crop_y2 = int(min(h, crop_y2))
                    crop_x2 = int(min(w, crop_x2))
                else:
                    crop_y1 = y1
                    crop_x1 = x1
                    crop_y2 = y2
                    crop_x2 = x2
            else:
                crop_y1 = y1
                crop_x1 = x1
                crop_y2 = y2
                crop_x2 = x2                
            
            crop_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            crop_lab = cv2.cvtColor(np.asarray(crop_img), cv2.COLOR_RGB2Lab)
            #print('crop_lab.size',crop_lab.size)
        
            all_in_fonts=word_in_font(chars,unsupport_chars,font_path)
            #print('all_in_fonts',all_in_fonts)
            # kk=np.linalg.norm(np.reshape(np.asarray(crop_lab),(-1,3)).std(axis=0))
            # print('kk',kk)
            if (np.linalg.norm(np.reshape(np.asarray(crop_lab),(-1,3)).std(axis=0))>55 or all_in_fonts) and retry<30:  # 颜色标准差阈值，颜色太丰富就不要了
                retry = retry+1                               
                #print('retry',retry)
                continue
            if not cf.customize_color:
                best_color = get_bestcolor(color_lib, crop_lab)
            else:
                r = random.choice([7,9,11,14,13,15,17,20,22,50,100])
                g = random.choice([8,10,12,14,21,22,24,23,50,100])
                b = random.choice([6,8,9,10,11,30,21,34,56,100])
                best_color = (r,g,b)                
            #print('best_color',best_color)
            break
        else:
            pass  
    #print('chars1',chars)        
    
    draw = ImageDraw.Draw(img)
    
    #隨機排序字串
    wordlist = list(chars)
    random.shuffle(wordlist)
    chars = ''.join(wordlist)

    #2021-09-04 
    DrawWordOutline = False
    if random.random() < cf.outlineword_probability:
        DrawWordOutline = True
    
    #2021-09-03 YOLO模式產圖
    if YOLOMode:
        YOLOLabelFileName =  save_file_number + '.txt'
        if int(save_file_number) <= cf.num_img * 0.8:
            YOLOfilePath = os.path.join('./YOLO/labels/train/', YOLOLabelFileName)
        else:
            YOLOfilePath = os.path.join('./YOLO/labels/val/', YOLOLabelFileName)
        
        with open(YOLOfilePath, 'w') as YOLOnewFile:
            for i, c in enumerate(chars):
                if DrawWordOutline:
                    DrawWordOntline(draw, best_color, x1, y1, c, font)
                else:    
                    draw.text((x1, y1), c, best_color, font=font)
                
                x_draw = min(x1+font_size, crop_x2) - 1
                y_draw = crop_y2 - 1
                #y_draw = min(y1+font_size, crop_y2) - 1

                # 測試畫rect框 (是否有辦法框住字)
                #shape = [(x1, y1), (x_draw, y_draw)] 
                #draw.rectangle(shape, fill=None, outline=(255, 0, 0))

                # 知道框哪裡就可以寫YOLO File了        
                imageWidth = abs(crop_x1 - crop_x2)
                imageHeight = abs(crop_y1 - crop_y2)
                # 在字典內才可寫入YOLO Label txt
                if c in WordDictionary:
                    YOLOLabelIndex = WordDictionary[c]
                    centerX = (x1 + x_draw) / 2 - crop_x1 
                    centerY = (y1 + y_draw) / 2 - crop_y1
                    centerX /= imageWidth
                    centerY /= imageHeight
                    width = abs(x1 - x_draw) / imageWidth
                    height = abs(y1 - y_draw) / imageHeight
                    writeInfo = "%s %f %f %f %f" % (YOLOLabelIndex, centerX, centerY, width, height)
                    YOLOnewFile.writelines(writeInfo)
                    YOLOnewFile.writelines('\n')
                x1 += (chars_size[i][0] + char_space_width)    
        YOLOnewFile.close()
    #原模式產圖
    else:
        for i, c in enumerate(chars):
            # self.draw_text_wrapper(draw, c, c_x, c_y - y_offset, font, word_color, force_text_border)
            #draw.text((x1, y1-y_offset), c, best_color, font=font)
            if DrawWordOutline:
                DrawWordOntline(draw, best_color, x1, y1, c, font)
            else:
                draw.text((x1, y1), c, best_color, font=font)  #best_color

            x1 += (chars_size[i][0] + char_space_width)
    
    crop_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    return crop_img, chars 

def DrawWordOntline(draw, best_color, x1, y1, c, font):
    offset = 2
    draw.text((x1-offset, y1), c, font=font, fill=best_color)
    draw.text((x1+offset, y1), c, font=font, fill=best_color)
    draw.text((x1, y1-offset), c, font=font, fill=best_color)
    draw.text((x1, y1+offset), c, font=font, fill=best_color)

    # 粗 thicker border
    draw.text((x1-offset, y1-offset), c, font=font, fill=best_color)
    draw.text((x1+offset, y1-offset), c, font=font, fill=best_color)
    draw.text((x1-offset, y1+offset), c, font=font, fill=best_color)
    draw.text((x1+offset, y1+offset), c, font=font, fill=best_color)
    #真正畫的字 最佳顏色反轉
    reverseColor = (abs(255 - best_color[0]), abs(255 - best_color[1]), abs(255 - best_color[2]))
    draw.text((x1, y1), c, reverseColor, font=font)  #best_color

def get_vertical_text_picture(image_file,color_lib,char_lines,fonts_list,font_unsupport_chars,cf):   
    img = Image.open(image_file)
    if img.mode != 'RGB':
        img = img.convert('RGB')
    w, h = img.size
    retry = 0
    while True:
                
        #随机获得不定长的文字
        chars = get_chars(char_lines)
        
        #随机选择一种字体
        font_path = random.choice(fonts_list)
        font_size = random.randint(cf.font_min_size,cf.font_max_size)
        
        #获得字体，及其大小
        font = ImageFont.truetype(font_path, font_size) 
        #不支持的字体文字，按照字体路径在该字典里索引即可    
        unsupport_chars = font_unsupport_chars[font_path]  
        
        ch_w = []
        ch_h = []
        for ch in chars:
            wt, ht = font.getsize(ch)
            ch_w.append(wt)
            ch_h.append(ht)
        f_w = max(ch_w)
        f_h = sum(ch_h)
        # 完美分割时应该取的,也即文本位置
        if h>f_h:
            x1 = random.randint(0, w - f_w)
            y1 = random.randint(0, h - f_h)
            x2 = x1 + f_w
            y2 = y1 + f_h            
                      
            if cf.random_offset:                
                # 随机加一点偏移，且随机偏移的概率占30%                
                rd = random.random()
                if rd < 0.3:  # 设定偏移的概率
                    crop_y1 = y1 - random.random() / 10 * f_h
                    crop_x1 = x1 - random.random() / 8 * f_h
                    crop_y2 = y2 + random.random() / 10 * f_h
                    crop_x2 = x2 + random.random() / 8 * f_h
                    crop_y1 = int(max(0, crop_y1))
                    crop_x1 = int(max(0, crop_x1))
                    crop_y2 = int(min(h, crop_y2))
                    crop_x2 = int(min(w, crop_x2))
                else:
                    crop_y1 = y1
                    crop_x1 = x1
                    crop_y2 = y2
                    crop_x2 = x2
            else:
                crop_y1 = y1
                crop_x1 = x1
                crop_y2 = y2
                crop_x2 = x2               
                                               
            crop_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
            crop_lab = cv2.cvtColor(np.asarray(crop_img), cv2.COLOR_RGB2Lab)
            
            all_in_fonts=word_in_font(chars,unsupport_chars,font_path)
            if (np.linalg.norm(np.reshape(np.asarray(crop_lab),(-1,3)).std(axis=0))>55 or all_in_fonts) and retry<30:  # 颜色标准差阈值，颜色太丰富就不要了
                retry = retry + 1
                continue
            if not cf.customize_color:
                best_color = get_bestcolor(color_lib, crop_lab)
            else:
                r = random.choice([7,9,11,14,13,15,17,20,22,50,100])
                g = random.choice([8,10,12,14,21,22,24,23,50,100])
                b = random.choice([6,8,9,10,11,30,21,34,56,100])
                best_color = (r,g,b)                
            break
        else:
            pass

    draw = ImageDraw.Draw(img)
    i = 0
    for ch in chars:
        draw.text((x1, y1), ch, best_color, font=font)
        y1 = y1 + ch_h[i]
        i = i + 1

    crop_img = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))
    crop_img = crop_img.transpose(Image.ROTATE_90)
    return crop_img,chars


def get_fonts(fonts_path):
    font_files = os.listdir(fonts_path)
    fonts_list=[]
    for font_file in font_files:
        font_path=os.path.join(fonts_path,font_file)
        fonts_list.append(font_path)
    return fonts_list
    

def get_unsupported_chars(fonts, chars_file):
    """
    Get fonts unsupported chars by loads/saves font supported chars from cache file
    :param fonts:
    :param chars_file:
    :return: dict
        key -> font_path
        value -> font unsupported chars
    """
    charset = load_chars(chars_file)
    charset = ''.join(charset)
    fonts_chars = get_fonts_chars(fonts, chars_file)
    fonts_unsupported_chars = {}
    for font_path, chars in fonts_chars.items():
        unsupported_chars = list(filter(lambda x: x not in chars, charset))
        fonts_unsupported_chars[font_path] = unsupported_chars
    return fonts_unsupported_chars

def load_chars(filepath):
    if not os.path.exists(filepath):
        print("Chars file not exists.")
        exit(1)

    ret = ''
    with open(filepath, 'r', encoding='utf-8') as f:
        while True:
            line = f.readline()
            if not line:
                break
            ret += line[0]
    return ret
def get_fonts_chars(fonts, chars_file):
    """
    loads/saves font supported chars from cache file
    :param fonts: list of font path. e.g ['./data/fonts/msyh.ttc']
    :param chars_file: arg from parse_args
    :return: dict
        key -> font_path
        value -> font supported chars
    """
    out = {}

    cache_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../', '.caches'))
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    chars = load_chars(chars_file)
    chars = ''.join(chars)

    for font_path in fonts:
        string = ''.join([font_path, chars])
        file_md5 = md5(string)

        cache_file_path = os.path.join(cache_dir, file_md5)

        if not os.path.exists(cache_file_path):
            ttf = load_font(font_path)
            _, supported_chars = check_font_chars(ttf, chars)
            print('Save font(%s) supported chars(%d) to cache' % (font_path, len(supported_chars)))

            with open(cache_file_path, 'wb') as f:
                pickle.dump(supported_chars, f, pickle.HIGHEST_PROTOCOL)
        else:
            with open(cache_file_path, 'rb') as f:
                supported_chars = pickle.load(f)
            print('Load font(%s) supported chars(%d) from cache' % (font_path, len(supported_chars)))

        out[font_path] = supported_chars

    return out

def load_font(font_path):
    """
    Read ttc, ttf, otf font file, return a TTFont object
    """

    # ttc is collection of ttf
    if font_path.endswith('ttc'):
        ttc = TTCollection(font_path)
        # assume all ttfs in ttc file have same supported chars
        return ttc.fonts[0]

    if font_path.endswith('ttf') or font_path.endswith('TTF') or font_path.endswith('otf'):
        ttf = TTFont(font_path, 0, allowVID=0,
                     ignoreDecompileErrors=True,
                     fontNumber=-1)

        return ttf
    
def md5(string):
    m = hashlib.md5()
    m.update(string.encode('utf-8'))
    return m.hexdigest()


def check_font_chars(ttf, charset):
    """
    Get font supported chars and unsupported chars
    :param ttf: TTFont ojbect
    :param charset: chars
    :return: unsupported_chars, supported_chars
    """
    #chars = chain.from_iterable([y + (Unicode[y[0]],) for y in x.cmap.items()] for x in ttf["cmap"].tables)
    chars_int=set()
    for table in ttf['cmap'].tables:
        for k,v in table.cmap.items():
            chars_int.add(k)            
            
    unsupported_chars = []
    supported_chars = []
    for c in charset:
        if ord(c) not in chars_int:
            unsupported_chars.append(c)
        else:
            supported_chars.append(c)

    ttf.close()
    return unsupported_chars, supported_chars


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
        
    parser.add_argument('--num_img', type=int, default=30, help="Number of images to generate")
    
    parser.add_argument('--font_min_size', type=int, default=40)
    parser.add_argument('--font_max_size', type=int, default=160,
                        help="Can help adjust the size of the generated text and the size of the picture")
    
    parser.add_argument('--bg_path', type=str, default='./background',
                        help='The generated text pictures will use the pictures of this folder as the background')
                        
    parser.add_argument('--fonts_path',type=str, default='./fonts/chinse_jian',
                        help='The font used to generate the picture')
    
    parser.add_argument('--corpus_path', type=str, default='./corpus', 
                        help='The corpus used to generate the text picture')
    
    parser.add_argument('--color_path', type=str, default='./models/colors_new.cp', 
                        help='Color font library used to generate text')
    
    parser.add_argument('--chars_file',  type=str, default='dict5990.txt',
                        help='Chars allowed to be appear in generated images')

    parser.add_argument('--customize_color', action='store_true', help='Support font custom color')
    
    parser.add_argument('--blur', action='store_true', default=False,
                        help="Apply gauss blur to the generated image")    
    
    parser.add_argument('--prydown', action='store_true', default=False,
                    help="Blurred image, simulating the effect of enlargement of small pictures")

    parser.add_argument('--lr_motion', action='store_true', default=False,
                    help="Apply left and right motion blur")
                    
    parser.add_argument('--ud_motion', action='store_true', default=False,
                    help="Apply up and down motion blur")

    parser.add_argument('--random_offset', action='store_true', default=True,
                help="Randomly add offset") 
    
    #将noise.yaml中noise.enable设置成true，生成图片将随机加入噪音
    parser.add_argument('--config_file', type=str, default='noise.yaml',
                    help='Set the parameters when rendering images')
      
    parser.add_argument('--output_dir', type=str, default='./output/', help='Images save dir')

    #不執行YOLO MODE? 輸出資料匯到指定資料夾
    parser.add_argument('--yolo_mode', action='store_true', default=False, help="YOLO Mode")
    #新增是否產生彩色影像
    parser.add_argument('--gray_image', action='store_true', default=False, help="Output Gray Image")
    #產生左右晃動圖的機率
    parser.add_argument('--lr_motion_probability', type=float, default = 0.2, help="left-right motion probability") 
    #產生上下晃動圖的機率
    parser.add_argument('--up_motion_probability', type=float, default = 0.1, help="up-down motion probability")
    #產生框線圖的機率
    parser.add_argument('--outlineword_probability', type=float, default = 0.1, help="out-line word probability")
    #單邊縮放的機率
    parser.add_argument('--resizeWH_probability', type=float, default = 0.2, help="resize Width Or Height probability")                     

    cf = parser.parse_args()
    
    #print('cf.config_file', cf.config_file)
    #flag = load_config(cf.config_file)
    #实例化噪音参数
    #noiser = Noiser(flag) 
    
    # 读入字体色彩库
    color_lib = FontColor(cf.color_path)
    # 读入字体
    print('color_lib',color_lib)
    fonts_path = cf.fonts_path

    # 读入newsgroup
    txt_root_path = cf.corpus_path
    char_lines = get_char_lines(txt_root_path = txt_root_path)

    #将该文件的字体以"路径+字体"的形式存放到列表中
    fonts_list = get_fonts(fonts_path)

    img_root_path = cf.bg_path
    imnames = os.listdir(img_root_path)
    imnames = GetFilterList(imnames, [".jpg", ".bmp", ".png"])
    
    #產圖前先清空label.txt檔案 與 資料夾
    labels_path = 'labels.txt'
    if os.path.exists(labels_path):
        os.remove(labels_path)
    if os.path.isdir(cf.output_dir):
        shutil.rmtree(cf.output_dir)
    os.mkdir(cf.output_dir)

    #YOLO mode處理機制
    YOLOMode = cf.yolo_mode
    if YOLOMode:
        YOLORoot = './YOLO/'
        if os.path.isdir(YOLORoot):
            shutil.rmtree(YOLORoot)
        os.mkdir(YOLORoot)
        os.mkdir(YOLORoot + 'images/')       
        os.mkdir(YOLORoot + 'images/train/')   #訓練影像Dir : ./YOLO/images/train/
        os.mkdir(YOLORoot + 'images/val/')     #驗證影像Dir : ./YOLO/images/val/
        os.mkdir(YOLORoot + 'labels/')
        os.mkdir(YOLORoot + 'labels/train/')   #訓練labels Dir : ./YOLO/labels/train/
        os.mkdir(YOLORoot + 'labels/val/')     #驗證label Dir : ./YOLO/labels/val/

    gs = 0
    #這段改掉，改成如果存在就刪掉檔案
    #if os.path.exists(labels_path):  # 支持中断程序后，在生成的图片基础上继续
    #    f = open(labels_path,'r',encoding='utf-8')
    #    lines = list(f.readlines())
    #    #print('lines',lines[1])
    #    f.close()
    #    gs = int(lines[-1].strip().split('.')[0].split('_')[1])
    #    print('Resume generating from step %d'%gs)
    #    print('gs',gs)

        
    #有哪些字的文件    
    chars_file = cf.chars_file
    
    #這個用來標註word label
    WordDictionary = {}
    WordDictionary.clear()
    currentIndex = 0
    
    char_directionaryfile = open(chars_file, 'r', encoding='utf-8')
    for word in char_directionaryfile.readlines():
      if word not in WordDictionary:
        WordDictionary[word.strip()] = currentIndex
        currentIndex += 1                
    char_directionaryfile.close

    '''
    返回的是字典，key对应font_path,value对应字体支持的字符
    '''
    font_unsupport_chars = get_unsupported_chars(fonts_list, chars_file)
    
    f = open(labels_path,'a',encoding='utf-8')
    print('start generating...')
    t0=time.time()
    img_n=0

    #要知道有多少的字串要產出
    nums_of_chars = len(char_lines)

    # 給定範圍
    for i in range(gs+1,cf.num_img+1):
        # 產生左右殘影圖
        blr_motion = False
        rdlr_motion = random.random()
        if rdlr_motion < cf.lr_motion_probability:    #設定產出左右偏移圖的機率
            blr_motion = True

        # 產生上下殘影圖
        bud_motion = False
        rdup_motion = random.random()
        if rdup_motion < cf.up_motion_probability:    #設定產出上下偏移圖的機率
            bud_motion = True

        # 如果以上兩個都有，優先使用左右殘影
        if blr_motion and bud_motion:
            bud_motion = False

        img_n+=1
        print('img_n',img_n)
        imname = random.choice(imnames)
        img_path = os.path.join(img_root_path,imname)

        #rnd = random.random()
        #if rnd<0.8: # 设定产生水平文本的概率
        #    gen_img, chars = get_horizontal_text_picture(img_path,color_lib,char_lines,fonts_list,font_unsupport_chars,cf)       
        #else:       #设定产生竖直文本的概率
        #    gen_img, chars = get_vertical_text_picture(img_path,color_lib,char_lines,fonts_list,font_unsupport_chars,cf)            
        #save_img_name = 'img_' + str(i).zfill(7) + '.jpg'
             
        index = i - 1
        if index > (nums_of_chars - 1):
          index %= nums_of_chars
        save_file_name = str(i)
        gen_img, chars = get_horizontal_text_picture(img_path,color_lib,char_lines,fonts_list,font_unsupport_chars,cf,index,save_file_name)    
        save_img_name = save_file_name + '.jpg'
        
        if gen_img.mode != 'RGB':
            gen_img= gen_img.convert('RGB')           
        
        #高斯模糊
        if cf.blur:
            image_arr = np.array(gen_img) 
            gen_img = apply_blur_on_output(image_arr)            
            gen_img = Image.fromarray(np.uint8(gen_img))
        #模糊图像，模拟小图片放大的效果
        if cf.prydown:
            image_arr = np.array(gen_img) 
            gen_img = apply_prydown(image_arr)
            gen_img = Image.fromarray(np.uint8(gen_img))
        #左右运动模糊
        if cf.lr_motion or blr_motion:
            image_arr = np.array(gen_img)
            gen_img = apply_lr_motion(image_arr)
            gen_img = Image.fromarray(np.uint8(gen_img))       
        #上下运动模糊       
        if cf.ud_motion or bud_motion:
            image_arr = np.array(gen_img)
            gen_img = apply_up_motion(image_arr)        
            gen_img = Image.fromarray(np.uint8(gen_img)) 

        print('gen_img2', gen_img)
    
        #雜訊處理有問題，先拿掉
        #if apply(flag.noise):
        #    gen_img = np.clip(gen_img, 0., 255.)
        #    gen_img = noiser.apply(gen_img)
        #    gen_img = Image.fromarray(np.uint8(gen_img))
        #    print('gen_img1',gen_img)

        #轉成灰階 (往後這裡可以多加一個arg參數，User可以選定是否要轉灰階)
        if cf.gray_image:
            gen_img = ImageOps.grayscale(gen_img)

        #2021-09-24 加入長寬單方向縮放
        resizeRandomValue = random.random()
        if resizeRandomValue < cf.resizeWH_probability:
            resizeWidth = gen_img.width
            resizeHeight = gen_img.height
            ZoomIn = random.uniform(1.25, 4)
            ZoomOut = random.uniform(0.25, 0.75)
            #一半機率放大、一半機率縮小
            if random.random() < 0.5:
                resizeRatio = ZoomIn
            else:
                resizeRatio = ZoomOut
            #一半機率縮縮放寬
            if random.random() < 0.5:
                resizeWidth = int(gen_img.width * resizeRatio)
            else:
                resizeHeight = int(gen_img.height * resizeRatio)
            gen_img = gen_img.resize((resizeWidth, resizeHeight))

        #存圖路徑修改
        #gen_img_path = ""
        if YOLOMode:
            if i <= cf.num_img * 0.8:
                gen_img_path = os.path.join('./YOLO/images/train/', save_img_name)
            else:
                gen_img_path = os.path.join('./YOLO/images/val/', save_img_name)    
        else:
            gen_img_path = os.path.join(cf.output_dir, save_img_name)
                
        gen_img.save(gen_img_path)

        f.write(save_img_name+ ' '+chars+'\n') #寫道Label.txt
        print('gennerating:-------'+save_img_name)
        # plt.figure()
        # plt.imshow(np.asanyarray(gen_img))
        # plt.show()
    t1=time.time()
    print('all_time',t1-t0)
    f.close()