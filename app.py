from flask import Flask, render_template, request, redirect, url_for, flash, send_file, Response
from pymongo import MongoClient
from bson.objectid import ObjectId
import csv
from io import StringIO
from math import ceil
import pandas as pd
import io


app = Flask(__name__)
client = MongoClient("mongodb://localhost:27017/")
db = client["Projects"]
products_collection = db["products"]


app.secret_key = 'your_secret_key'
@app.route('/')
def index():
    return redirect(url_for('product_list', page=1))

@app.route('/product-list', methods=['GET'])
def product_list():
    page = int(request.args.get('page', 1))
    per_page = 10

    # Lấy tiêu chí sắp xếp, mặc định là `product_id`
    sort_by = request.args.get('sort_by', 'product_id')
    sort_criteria = {"product_id": 1} if sort_by == "product_id" else {"name": 1}

    # Lấy tất cả sản phẩm, sắp xếp theo tiêu chí
    all_products = list(products_collection.find().sort(list(sort_criteria.items())))

    # Cập nhật lại thứ tự `product_id` nếu không liên tục
    for index, product in enumerate(all_products):
        if "product_id" not in product:
            expected_product_id = f"Sp{index + 1:03d}"
            products_collection.update_one({"_id": product["_id"]}, {"$set": {"product_id": expected_product_id}})
        else:
            expected_product_id = f"Sp{index + 1:03d}"
            if product["product_id"] != expected_product_id:
                products_collection.update_one({"_id": product["_id"]}, {"$set": {"product_id": expected_product_id}})

    # Lấy lại sản phẩm sau khi đã cập nhật
    total_products = products_collection.count_documents({})
    total_pages = ceil(total_products / per_page)
    products = list(products_collection.find().sort(list(sort_criteria.items())).skip((page - 1) * per_page).limit(per_page))

    return render_template(
        'index.html',
        products=products,
        page=page,
        total_pages=total_pages,
        sort_by=sort_by
    )

@app.route('/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_id = request.form.get('product_id')
        name = request.form.get('name')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))

        if products_collection.find_one({"product_id": product_id}):
            flash("ID sản phẩm đã tồn tại!", "error")
            return redirect(url_for('add_product'))

        products_collection.insert_one({
            "product_id": product_id,
            "name": name,
            "quantity": quantity,
            "price": price
        })
        flash("Sản phẩm đã được thêm thành công!", "success")
        return redirect(url_for('product_list', page=1))

    return render_template('add_product.html')


@app.route('/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = products_collection.find_one({"product_id": product_id})

    if not product:
        flash("Sản phẩm không tồn tại!", "error")
        return redirect(url_for('product_list', page=1))

    if request.method == 'POST':
        name = request.form.get('name')
        quantity = int(request.form.get('quantity'))
        price = float(request.form.get('price'))

        products_collection.update_one(
            {"product_id": product_id},
            {"$set": {"name": name, "quantity": quantity, "price": price}}
        )
        flash("Sản phẩm đã được cập nhật!", "success")
        return redirect(url_for('product_list', page=1))

    return render_template('edit_product.html', product=product)

@app.route('/delete/<product_id>')
def delete_product(product_id):
    result = products_collection.delete_one({"product_id": product_id})
    if result.deleted_count == 1:
        flash("Sản phẩm đã được xóa!", "success")
    else:
        flash("Không tìm thấy sản phẩm để xóa!", "error")
    return redirect(url_for('product_list', page=1))

@app.route('/search', methods=['GET'])
def search_product():
    query = request.args.get('query', '').strip()
    page = int(request.args.get('page', 1))
    per_page = 10
    if not query:
        flash(('error', 'Vui lòng nhập từ khóa tìm kiếm!'))
        return render_template('index.html', products=[], page=1, total_pages=1, query='', no_products_found=True)
    search_filter = {
        "$or": [
            {"name": {"$regex": query, "$options": 'i'}},
            {"product_id": {"$regex": query, "$options": 'i'}}
        ]
    }
    total_products = products_collection.count_documents(search_filter)

    if total_products == 0:
        flash(('error', f"Không tìm thấy sản phẩm nào với từ khóa '{query}'"))
        return render_template('index.html', products=[], page=1, total_pages=1, query=query, no_products_found=True)

    # Phân trang
    total_pages = ceil(total_products / per_page)
    products_cursor = products_collection.find(search_filter).skip((page - 1) * per_page).limit(per_page)
    products = list(products_cursor)

    return render_template(
        'index.html',
        products=products,
        page=page,
        total_pages=total_pages,
        query=query,
        no_products_found=len(products) == 0,
        total_products=total_products
    )



@app.route('/calculate', methods=['GET'])
def calculate_product():
    products = list(products_collection.find())
    unique_product_names = list(set(product['name'] for product in products))
    product_name = request.args.get('product_name', '')
    if product_name:
        filtered_products = [product for product in products if product['name'] == product_name]
    else:
        filtered_products = products
    total_quantity = 0
    total_value = 0.0
    for product in filtered_products:
        total_quantity += product['quantity']
        total_value += product['quantity'] * product['price']

    return render_template('calculate_product.html', 
                           unique_product_names=unique_product_names,
                           products=products, 
                           filtered_products=filtered_products,
                           total_quantity=total_quantity, 
                           total_value=total_value, 
                           product_name=product_name)

@app.route('/import_csv', methods=['POST'])
def import_csv():
    if 'file' not in request.files:
        flash("No file part", "error")
        return redirect(url_for('product_list', page=1))

    file = request.files['file']
    if file.filename == '':
        flash("No selected file", "error")
        return redirect(url_for('product_list', page=1))

    if not file.filename.endswith('.csv'):
        flash("File không đúng định dạng CSV!", "error")
        return redirect(url_for('product_list', page=1))

    try:
        file_content = file.read().decode('utf-8-sig')
        csv_data = csv.DictReader(StringIO(file_content))

        if not csv_data:
            flash("File CSV không có dữ liệu!", "error")
            return redirect(url_for('product_list', page=1))

        for row in csv_data:
            product_id = row.get('product_id')
            if not product_id:
                flash("ID sản phẩm không được để trống trong dòng dữ liệu!", "error")
                continue

            name = row.get('name')
            quantity = int(row.get('quantity', 0)) if row.get('quantity') else 0
            price = float(row.get('price', 0.0)) if row.get('price') else 0.0

            existing_product = products_collection.find_one({"product_id": product_id})
            if existing_product:
                products_collection.update_one(
                    {"product_id": product_id},
                    {"$set": {"name": name, "quantity": quantity, "price": price}}
                )
            else:
                products_collection.insert_one({
                    "product_id": product_id,
                    "name": name,
                    "quantity": quantity,
                    "price": price
                })

        flash("Import dữ liệu thành công!", "success")
    except UnicodeDecodeError as e:
        flash(f"Lỗi mã hóa khi đọc file: {e}", "error")
    except Exception as e:
        flash(f"Lỗi trong quá trình import: {e}", "error")

    return redirect(url_for('product_list', page=1))

@app.route('/export', methods=['GET'])
def export_products():
    products = products_collection.find()
    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=['_id', 'name', 'quantity', 'price'])
    writer.writeheader()
    for product in products:
        writer.writerow({
            '_id': str(product['_id']),
            '_id': product.get('_id', ''),
            'name': product.get('name', ''),
            'quantity': product.get('quantity', ''),
            'price': product.get('price', '')
        })

    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={"Content-Disposition": "attachment;filename=products.csv"}
    )

if __name__ == '__main__':
    app.run(debug=True)
