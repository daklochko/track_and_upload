import os
import time
import json
import dropbox
import streamlit as st
from pathlib import Path
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit_autorefresh import st_autorefresh
from dropbox.oauth import DropboxOAuth2Flow

APP_KEY = st.secrets["DROPBOX_APP_KEY"]
APP_SECRET = st.secrets["DROPBOX_APP_SECRET"]

def get_files_in_folder(folder):
    return {f for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))}

def upload_file_to_dropbox(local_path, dropbox_path, dropbox_token):
    dbx = dropbox.Dropbox(dropbox_token)
    with open(local_path, "rb") as f:
        dbx.files_upload(f.read(), dropbox_path, mode=dropbox.files.WriteMode.overwrite)
    print(f"Загружен файл {local_path}")

def sync_files(local_folder, dropbox_folder, dropbox_token):
    
    if "uploaded_files" not in st.session_state:
        st.session_state.uploaded_files = set()

    if not os.path.exists(local_folder):
        st.error(f"Локальная папка {local_folder} не найдена")
        return

    current_files = get_files_in_folder(local_folder)
    new_files = current_files - st.session_state.uploaded_files

    for file_name in new_files:
        try:
            local_path = os.path.join(local_folder, file_name)
            dropbox_path = os.path.join(dropbox_folder, file_name).replace("\\", "/")
            upload_file_to_dropbox(local_path, dropbox_path, dropbox_token)
            st.session_state.uploaded_files.add(file_name)
            st.success(f"Загружен файл: {file_name}")
        except Exception as e:
            st.error(f"Ошибка при загрузке {file_name}: {e}")

def main():
    
    st.set_page_config("Загрузка в Dropbox")
    st.title("Загрузка в Dropbox")

    if "access_token" not in st.session_state:
        auth_flow = dropbox.DropboxOAuth2FlowNoRedirect(APP_KEY, APP_SECRET)

        authorize_url = auth_flow.start()
        st.markdown(f"[Авторизация Dropbox]({authorize_url})")

        code = st.text_input("После авторизации вставьте код из Dropbox:")

        if st.button("Отправить код доступа"):
            try:
                oauth_result = auth_flow.finish(code.strip())
                st.session_state.access_token = oauth_result.access_token
                st.success("Авторизация прошла успешно!")
            except Exception as e:
                st.error(f"Ошибка авторизации: {e}")
    else:
        st.success("Вы авторизованы!")
        dbx = dropbox.Dropbox(st.session_state.access_token)
        try:
            account = dbx.users_get_current_account()
            st.write(f"Привет, {account.name.display_name}!")
        except Exception as e:
            st.error(f"Ошибка при получении информации о пользователе: {e}")

    with st.form("settings_form"):
        local_folder = st.text_input("Локальная папка", value=st.session_state.get("local_folder", ""))
        dropbox_folder = st.text_input("Папка в Dropbox", value=st.session_state.get("dropbox_folder", "/"))

        submitted = st.form_submit_button("Сохранить настройки")

        if submitted:
            st.session_state.local_folder = local_folder
            st.session_state.dropbox_folder = dropbox_folder
            st.success("Настройки сохранены!")

    required_fields = ["local_folder", "dropbox_folder"]
    
    if not all(st.session_state.get(field) for field in required_fields):
        st.warning("Заполните все поля")
        return

    if "running" not in st.session_state:
        st.session_state.running = False

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Старт"):
            st.session_state.running = True
    with col2:
        if st.button("Стоп"):
            st.session_state.running = False

    if st.session_state.running:
        st_autorefresh(interval=60*1000, limit=None, key="autorefresh")
        st.info("Программа работает")
        sync_files(
            st.session_state.local_folder,
            st.session_state.dropbox_folder,
            st.session_state.access_token
        )
    else:
        st.info("Программа остановлена")

if __name__ == "__main__":
    main()