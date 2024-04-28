# -*- coding: utf-8 -*-
import os
import re
import fitz
import pandas as pd
from tqdm import tqdm
from PIL import Image
from decimal import Decimal
from paddleocr import PaddleOCR


def get_all_files(dirs):
    all_files = []
    for subdir, _, files in os.walk(dirs):
        for file in files:
            all_files.append(os.path.join(subdir, file))
    return all_files


def save_img_path(pth, flg):
    base = os.path.basename(root_dir)
    # 分解路径
    parts = pth.split('/')
    # 处理路径中的每个部分
    for i, part in enumerate(parts):
        if part == base:
            parts[i] += '识别后'
            parts.insert(i + 1, flg)
    # 重新构建路径
    new_path = '/'.join(parts)
    save_dir = os.path.dirname(new_path)
    return save_dir


def pdf2img(file_path):
    pdf_document = fitz.open(file_path)
    page = pdf_document.load_page(0)
    pm = page.get_pixmap(matrix=fitz.Matrix(2, 2))
    # 如果宽度或高度大于2000像素，则不放大图像
    if pm.width > 2000 or pm.height > 2000:
        pm = page.get_pixmap(matrix=fitz.Matrix(1, 1))
    # 将图像数据转换为RGB模式
    img = Image.frombytes('RGB', [pm.width, pm.height], pm.samples)
    return img


def ocr_pdf(file_path):
    ocr = PaddleOCR(
        use_angle_cls=True,
        lang='ch',
        page_num=1,
        show_log=False,
        use_gpu=True)
    result = ocr.ocr(file_path, cls=True)
    texts = [line[1][0] for line in result[0]]
    print(texts)
    return texts


def extract_name(image_path):
    match = re.search(r'(?<=/)[^/]+/[^/]+/(?P<content>[^/]+)(?=/)', image_path)
    if match:
        path_name = match.group('content')
        return path_name
    else:
        print("未匹配到姓名")
        return ''


def total_mount_process(amount_list):
    # 处理商品总金额、商品总税额、价税合计
    # a=total_amount, b=total_tax_amount, c=total_price_and_tax
    # 添加默认返回值
    a = Decimal(0)
    b = Decimal(0)
    c = Decimal(0)
    if not amount_list:
        c = Decimal(0)
        a = Decimal(0)
        b = Decimal(0)
    elif len(amount_list) == 1:
        c = Decimal(amount_list[0])
        a = c
        b = Decimal(0)
    elif len(amount_list) == 2:
        c = Decimal(amount_list[1])
        a = Decimal(amount_list[0])
        b = c - a
    elif len(amount_list) in [3, 4]:
        c = Decimal(amount_list[2])
        a = Decimal(amount_list[0])
        b = Decimal(amount_list[1])
    elif len(amount_list) == 5:
        c = Decimal(amount_list[-1])
        a = Decimal(amount_list[-3])
        b = Decimal(amount_list[-2])
    return a, b, c


def name_process(name_list):
    buyer = name_list[0] if len(name_list) > 0 else ''
    seller = name_list[1] if len(name_list) > 1 else ''
    return buyer, seller


if __name__ == '__main__':

    root_dir = '../data/202403账期'
    df1, df2, df3, df4, df5, df6, df7, df8, df9, df10, df11, df12, df13, df14 = [
    ], [], [], [], [], [], [], [], [], [], [], [], [], []

    start_index = 0
    pdf_paths = get_all_files(root_dir)
    for pdf_path in tqdm(
            pdf_paths[start_index:],
            desc='Processing images',
            unit='image'):
        print('路径：', pdf_path)
        invoice_data = ocr_pdf(pdf_path)

        # 账期
        accounting_period = os.path.basename(root_dir)
        # 姓名
        name = extract_name(pdf_path)
        # 发票号码
        invoice_number_match = re.search(
            r'发票号码[：:]{1}\s?[：:]?\s?(\d+)\s',
            ' '.join(invoice_data))
        invoice_number = invoice_number_match.group(
            1) if invoice_number_match else None
        # 开票日期
        invoice_date_match = re.search(
            r'(\d+年\d+月\d+日)', ' '.join(invoice_data))
        invoice_date = invoice_date_match.group(
            1) if invoice_date_match else None
        # 购买方、销售方
        name_pattern = r'称\s?[：:·]{1}\s?(.+?)\s'  # 称(?:[^ ])([^ ]+?)\s
        names_match = re.findall(name_pattern, ' '.join(invoice_data))
        buyer_name, seller_name = name_process(names_match)
        # 商品总金额、商品总税额、价税合计
        money = r'(?:计\s?|￥|¥|）￥)\s?([0-9]\d{0,9}(?:\.\d{2}))\s'
        amount = re.findall(money, ' '.join(invoice_data))
        total_amount, total_tax_amount, total_price_and_tax = total_mount_process(
            amount)
        # 购买方纳税人识别号
        # r'纳税人识别号\s*[:：]\s*(\w{18})\s*'
        buyer_tax_id_pattern = r'纳税人识别号\S?[：:]{1}\s?(\w{18})\s'
        buyer_tax_ids = re.findall(
            buyer_tax_id_pattern,
            ' '.join(invoice_data))
        buyer_tax_id = buyer_tax_ids[0] if buyer_tax_ids else None
        # 货物名称
        good_name_pattern = r'\*[\u4e00-\u9fa5]+.*?\*.*?(?=\s)'
        good_names = re.findall(good_name_pattern, ' '.join(invoice_data))
        good_name = ' '.join(good_names)if good_names else '(详见销货清单)'
        # 货物编号
        good_number = len(good_names) if good_names else 1
        # 是否合规
        is_compliant = 1
        # 不合规原因
        non_compliance_reason = ''
        flag = 'invoice'
        # 输出是否合规和不合规原因
        try:
            if not invoice_number:
                raise Exception('发票号码字段缺失')
            if not invoice_date:
                raise Exception('开票日期字段缺失')
            if not buyer_name:
                raise Exception('购买方名称字段缺失')
            if not seller_name:
                raise Exception('销售方名称字段缺失')
            if not amount:
                raise Exception('无商品金额')
            if not buyer_tax_id:
                raise Exception('购买方纳税人识别号字段缺失')
            if (Decimal(total_amount) + Decimal(total_tax_amount)
                    ) != Decimal(total_price_and_tax):
                raise Exception('价税合计与商品总金额和商品总税额不相等')

            # 如果所有字段都存在，则打印它们
            print('发票号码:', invoice_number)
            print('开票日期:', invoice_date)
            print('购买方名称:', buyer_name)
            print('商品总金额:', total_amount)
            print('商品总税额:', total_tax_amount)
            print('价税合计:', total_price_and_tax)
            print('购买方纳税人识别号:', buyer_tax_id)
            print('销售方名称:', seller_name)
            print('货物名称:', good_name)
            print('货物编号:', good_number)

        except Exception as e:
            is_compliant = 0
            non_compliance_reason = '发票信息不完整或格式不合规，原因：' + str(e)
            print('是否合规:', is_compliant)
            # 根据情况修改 flag
            flag = 'problem'
            print('不合规原因:', non_compliance_reason)

        # 在这里根据 flag 调用 save_img_path() 函数
        save_image_dir = save_img_path(pdf_path, flag)
        os.makedirs(save_image_dir, exist_ok=True)
        file_name = os.path.splitext(os.path.basename(pdf_path))[0]
        if flag == 'invoice':
            save_image_path = os.path.join(
                save_image_dir, invoice_number + '.png')
        else:
            save_image_path = os.path.join(save_image_dir, file_name + '.png')

        # 保存图像
        pdf2img(pdf_path).save(save_image_path, 'PNG')

        df1.append(accounting_period)
        df2.append(name)
        df3.append(invoice_number)
        df4.append(invoice_date)
        df5.append(buyer_name)
        df6.append(total_amount)
        df7.append(total_tax_amount)
        df8.append(total_price_and_tax)
        df9.append(buyer_tax_id)
        df10.append(seller_name)
        df11.append(good_name)
        df12.append(good_number)
        df13.append(is_compliant)
        df14.append(non_compliance_reason)

    # 创建新的 DataFrame
    df_new = pd.DataFrame({
        '账期': df1,
        '姓名': df2,
        '发票号码': df3,
        '开票日期': df4,
        '购买方名称': df5,
        '商品总金额': df6,
        '商品总税额': df7,
        '价税合计': df8,
        '购买方纳税人识别号': df9,
        '销售方名称': df10,
        '货物名称': df11,
        '货物编号': df12,
        '是否合规': df13,
        '不合规原因': df14
    })
    # 构建保存文件的路径
    save_excel_path = os.path.join(
        root_dir + '识别后',
        os.path.basename(root_dir))
    # 保存数据到 Excel 文件
    df_new.to_excel(save_excel_path + '.xlsx', index=False)
    print('数据已保存到 Excel 文件中！')
