
# OCR_Image_Generator

該工具修改擴充 : [Color_OCR_image_generator](https://github.com/zcswdt/Color_OCR_image_generator)
增加Arguments參數以產出更多樣性的文字圖。這些圖片可作為訓練OCR模型的訓練資料。


## 使用說明
該工具可依據自行找到的背景、字體，並設定要產生的字串，生成包含文字的圖片。
* 字體檔案放在 `\OCR_Image_Generator\fonts\chinse_jian\`  資料夾底下。
![](https://i.imgur.com/rXOqv6H.png =600x300)


* 背景圖放在`\OCR_image_Generator\background\` 資料夾底下。
![](https://i.imgur.com/yy6YbWf.png)



* 要生成的字串放在`\OCR_image_Generator\corpus\` 資料夾底下。
![](https://i.imgur.com/rPmDUeC.png)


## 擴充Arguments說明
### `--yolo_mode`: 是否開啟YOLO標註模式?
* 前置作業 : 要先準備好`GenerateChar.txt`檔案，程式會依照檔案內字的順序標註 YOLO 模型需要的Label ID。
![](https://i.imgur.com/9B1vf25.png)

* 執行程式輸出成果會放到`\OCR_image_Generator\YOLO\`，並按照8 : 2區分訓練資料以及驗證資料。



### `--gray_image`: 產出影像是否轉為灰階?
* 開啟該參數輸出圖片會變為灰階圖。

![](https://i.imgur.com/hOGsVnd.png)



### `--lr_motion_probability`: 產生左右晃動圖的機率 (0~1)
* 原程式`--lr_motion`功能，只要開啟必會產出左右晃動的圖片，由於希望透過該工具產出大量訓練資料，改為輸入機率產出較能模擬真實情況。

![](https://i.imgur.com/J8Z0nmL.png)


### `--up_motion_probability`: 產生上下晃動圖的機率 (0~1)
* 原程式`--up_motion`功能，只要開啟必會產出上下晃動的圖片，由於希望透過該工具產出大量訓練資料，改為輸入機率產出較能模擬真實情況。

![](https://i.imgur.com/GKVZCHw.png)


### `--outlineword_probability`: 產生包含文字邊框圖的機率 (0~1)
* 真實場景中會發現有許多包含邊框的文字，若是能產生該種資料可增加訓練資料的多樣性。

![](https://i.imgur.com/GuL8UeO.png)



### `--resizeWH_probability`: 產生單邊縮放圖的機率 (0~1)
* YOLO的data augmentation scale參數，會固定長寬比進行縮放，並未模擬到沿邊單邊縮放的情形，而真實場景中常見被拉長或是被壓扁的字，若是能產生該種資料可增加訓練資料的多樣性。

![](https://i.imgur.com/rN5Mcuv.png)




## 生成資料Demo
使用Colab : **OCR_Generate.ipynb** :  <a href="https://colab.research.google.com/drive/139BK2WuNYQGjGJ3l1VPhaFbMKz3I9tFI" target="_blank"><img src="https://colab.research.google.com/assets/colab-badge.svg" alt="Open In Colab"/></a> 

DEMO GIF :
![](https://i.imgur.com/uHLujW4.gif)














