import streamlit as st
from pymongo import MongoClient
import pandas as pd

MONGO_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "Projects"
COLLECTION_NAME = "products"

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]
products_collection = db[COLLECTION_NAME]


def main():
    st.title("Quản lý sản phẩm")
    menu = ["Thêm sản phẩm", "Danh sách sản phẩm", "Tìm kiếm", "Import/Export CSV"]
    choice = st.sidebar.selectbox("Chọn chức năng", menu)

    if choice == "Thêm sản phẩm":
        add_product()
    elif choice == "Danh sách sản phẩm":
        show_products()
    elif choice == "Tìm kiếm":
        search_product()
    elif choice == "Import/Export CSV":
        import_export_csv()

def add_product():
    st.subheader("Thêm sản phẩm mới")
    name = st.text_input("Tên sản phẩm")
    quantity = st.number_input("Số lượng", min_value=1, step=1)
    price = st.number_input("Giá", min_value=0.0, step=1.0)


    if st.button("Thêm sản phẩm"):
        if name:
            new_product = {"name": name, "quantity": quantity, "price": price}
            products_collection.insert_one(new_product)
            st.success(f"Sản phẩm {name} đã được thêm thành công!")
        else:
            st.error("Vui lòng nhập tên sản phẩm!")

def show_products():
    st.subheader("Danh sách sản phẩm")
    products = list(products_collection.find())
    if products:
        df = pd.DataFrame(products)
        st.dataframe(df[["_id", "name", "quantity", "price"]])
    else:
        st.warning("Không có sản phẩm nào!")

    if st.button("Làm mới danh sách"):
        st.experimental_rerun()

def search_product():
    st.subheader("Tìm kiếm sản phẩm")
    search_term = st.text_input("Nhập tên sản phẩm cần tìm")
    if st.button("Tìm kiếm"):
        results = list(products_collection.find({"name": {"$regex": search_term, "$options": "i"}}))
        if results:
            df = pd.DataFrame(results)
            st.write("Danh sách các sản phẩm tìm được:")
            st.dataframe(df[["_id", "name", "quantity", "price"]])

            total_quantity = df["quantity"].sum()
            total_price = (df["quantity"] * df["price"]).sum()
            st.write(f"Tổng số lượng sản phẩm: {total_quantity}")
            st.write(f"Tổng số tiền: {total_price} VND")
        else:
            st.warning("Không tìm thấy sản phẩm nào!")

def import_export_csv():
    st.subheader("Import/Export CSV")

    uploaded_file = st.file_uploader("Chọn file CSV", type="csv")
    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        data = df.to_dict(orient="records")
        products_collection.insert_many(data)
        st.success("Dữ liệu đã được import thành công!")

    if st.button("Export CSV"):
        products = list(products_collection.find())
        df = pd.DataFrame(products)
        csv = df.to_csv(index=False)
        st.download_button(label="Tải CSV", data=csv, file_name="products.csv", mime="text/csv")

if __name__ == "__main__":
    main()
