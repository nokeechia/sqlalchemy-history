import pytest
import sqlalchemy as sa
from sqlalchemy_history import version_class
from tests import TestCase


class TestValidityStrategy(TestCase):
    def create_models(self):
        class BlogPost(self.Model):
            __tablename__ = "blog_post"
            __versioned__ = {"base_classes": (self.Model,), "strategy": "validity"}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            name = sa.Column(sa.Unicode(255))

        class Article(self.Model):
            __tablename__ = "article"
            __versioned__ = {"base_classes": (self.Model,), "strategy": "validity"}
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            name = sa.Column(sa.Unicode(255))

        self.BlogPost = BlogPost
        self.Article = Article

    def test_schema_contains_end_transaction_id(self):
        table = version_class(self.Article).__table__
        assert "end_transaction_id" in table.c
        table.c.end_transaction_id
        assert table.c.end_transaction_id.nullable
        assert not table.c.end_transaction_id.primary_key

    def test_end_transaction_id_none_for_newly_inserted_record(self):
        article = self.Article(name="Something")
        self.session.add(article)
        self.session.commit()
        assert article.versions[-1].end_transaction_id is None

    def test_updated_end_transaction_id_of_previous_version(self):
        article = self.Article(name="Something")
        self.session.add(article)
        self.session.commit()

        article.name = "Some other thing"
        self.session.commit()
        assert article.versions[-2].end_transaction_id == article.versions[-1].transaction_id


class TestJoinTableInheritanceWithValidityVersioning(TestCase):
    def create_models(self):
        class TextItem(self.Model):
            __tablename__ = "text_item"
            __versioned__ = {
                "base_classes": (self.Model,),
                "strategy": "validity",
            }
            id = sa.Column(
                sa.Integer, sa.Sequence(f"{__tablename__}_seq"), autoincrement=True, primary_key=True
            )

            discriminator = sa.Column(sa.Unicode(100))

            __mapper_args__ = {
                "polymorphic_on": discriminator,
            }

        class Article(TextItem):
            __tablename__ = "article"
            __mapper_args__ = {"polymorphic_identity": "article"}
            id = sa.Column(
                sa.Integer,
                sa.ForeignKey(TextItem.id),
                sa.Identity(always=False, on_null=True),
                autoincrement=True,
                primary_key=True,
            )

        class BlogPost(TextItem):
            __tablename__ = "blog_post"
            __mapper_args__ = {"polymorphic_identity": "blog_post"}
            id = sa.Column(
                sa.Integer,
                sa.ForeignKey(TextItem.id),
                sa.Identity(always=False, on_null=True),
                autoincrement=True,
                primary_key=True,
            )

        self.TextItem = TextItem
        self.Article = Article
        self.BlogPost = BlogPost

    @pytest.fixture(autouse=True)
    def setup_method_for_table_inhritance(self, setup_session):
        self.TextItemVersion = version_class(self.TextItem)
        self.ArticleVersion = version_class(self.Article)
        self.BlogPostVersion = version_class(self.BlogPost)
        yield
        del self.TextItemVersion, self.ArticleVersion, self.BlogPostVersion

    def test_all_tables_contain_transaction_id_column(self):
        assert "end_transaction_id" in self.TextItemVersion.__table__.c
        assert "end_transaction_id" in self.ArticleVersion.__table__.c
        assert "end_transaction_id" in self.BlogPostVersion.__table__.c
