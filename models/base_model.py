import enum
from sqlalchemy import Integer, String, Text, Column, DateTime, ForeignKey, BigInteger, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
from sqlalchemy.orm import relationship
from sqlalchemy import Enum
from enum import Enum as PyEnum

Base = declarative_base()



class BaseModel(Base):
    __abstract__ = True
    created_at = Column(DateTime, default=datetime.now)


class OrderType(PyEnum):
    SALE = "sale"
    RENT = "rent"
    

class OrderStatus(PyEnum):
    WAITING = "waiting"
    APPROVED = "approved"
    REJECTED = "rejected"



class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, index=True, nullable=False, unique=True)
    name = Column(String)
    surname = Column(String)
    username = Column(String, unique=True)
    date = Column(DateTime, default=datetime.now)
    phone = Column(String)
    bio = Column(String)
    language = Column(String, nullable=False, default='ru')
    
    orders = relationship("Order", back_populates="user")





class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    state = Column(String(70),  nullable=False, index=True)
    region = Column(String(70),  nullable=True,  index=True)  # сделай nullable=True, если не всегда вводится
    city = Column(String(70),  nullable=False, index=True)
    address_line = Column(String(255),  nullable=True,  index=True)

    orders = relationship("Order", back_populates="address")





class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(70), nullable=False, index=True)
    description = Column(String(255), nullable=False, index=True)
    photos = Column(Text, nullable=False, index=True)
    price = Column(String,     nullable=False, index=True)
    phone = Column(String, nullable=False, index=True)
    type = Column(Enum(OrderType), nullable=False, index=True)
    status = Column(Enum(OrderStatus), nullable=False, index=True, default=OrderStatus.WAITING)
    user_id = Column(BigInteger, ForeignKey("users.user_id"))
    address_id = Column(Integer, ForeignKey("addresses.id")) 
    is_published  = Column(Boolean, default=False, nullable=False, index=True)
    published_at  = Column(DateTime, nullable=True)

    user    = relationship("User",    back_populates="orders")
    address = relationship("Address", back_populates="orders")





class Advertisements(Base):
    __tablename__ = 'advertisements'

    id = Column(Integer, primary_key=True, index=True)
    ad_uuid = Column(Text, index=True, nullable=False)
    content = Column(Text)
    media_type = Column(String)  # Лучше String, т.к. типы ограничены (text, photo, video, gif)
    media_file_id = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    target_lang = Column(String)  # "ru", "en" или None
    is_active = Column(Boolean, default=True)
    deliveries = relationship("AdvertisementsDeliveries", backref="ad", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("ad_uuid", "target_lang", name="ix_advertisements_ad_uuid_lang"),
    )

    def to_dict(self):
        return {
            "ad_uuid": self.ad_uuid,
            "target_lang": self.target_lang,
            "content": self.content
        }


class AdvertisementsDeliveries(Base):
    __tablename__ = 'advertisements_deliveries'

    id = Column(Integer, primary_key=True, index=True)
    ad_id = Column(Integer, ForeignKey("advertisements.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(BigInteger, index=True, nullable=False)
    message_id = Column(BigInteger, index=True, nullable=False)  # Лучше как число
    sent_at = Column(DateTime, default=datetime.now)

    def to_dict(self):
        return {
            "ad_uuid": self.ad_uuid,
            "target_lang": self.target_lang,
            "content": self.content
        }
















  