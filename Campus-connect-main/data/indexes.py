from data.mongo_client import users_col, projects_col, messages_col


def create_indexes():
    # USERS
    users_col.create_index("django_user_id", unique=True)
    users_col.create_index("degree")
    users_col.create_index("skills")          # para find_users_by_skill

    # PROJECTS
    projects_col.create_index("owner_django_user_id")
    projects_col.create_index("needed_skills")   # para find_projects_by_skill
    projects_col.create_index(
        [("title", "text"), ("description", "text")],
        name="project_text_search"
    )

    # MESSAGES
    messages_col.create_index([("project_id", 1), ("ts", 1)])


if __name__ == "__main__":
    print("Creando índices en MongoDB...")
    create_indexes()
    print("OK")
