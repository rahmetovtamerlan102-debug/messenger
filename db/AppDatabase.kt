package com.example.messenger.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteOpenHelper
import net.sqlcipher.database.SupportFactory

@Database(entities = [MessageEntity::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao

    companion object {
        @Volatile
        private var INSTANCE: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase {
            return INSTANCE ?: synchronized(this) {
                val passphrase = "your-encryption-key"  // хранить безопасно
                val factory = SupportFactory(passphrase.toByteArray())
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "messenger.db"
                )
                    .openHelperFactory(factory)
                    .build()
                INSTANCE = instance
                instance
            }
        }
    }
}
