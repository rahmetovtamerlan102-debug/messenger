package com.example.messenger.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity
data class MessageEntity(
    @PrimaryKey val id: String,
    val chatId: String,
    val senderId: Int,
    val senderName: String,
    val text: String,
    val mediaUrl: String?,
    val timestamp: String,
    val isDeleted: Boolean
)
